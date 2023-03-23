import struct
import itertools
import hashlib
import os.path
import inspect
from importlib.machinery import SourceFileLoader


def generate_code(
    fields, pkt_class, generate_for_pack, generate_for_unpack,
    sourcecode_by_field_name, vectorize
):
    if not generate_for_pack and not generate_for_unpack:
        return

    # Divide the fields into groups where each group share the same value
    # fof the 'is_fixed' attribute.
    grouped_by_variability = [
        (k, list(g))
        for k, g in itertools.groupby(fields, lambda i_n_f: i_n_f[2].is_fixed)
    ]

    # Generate code for each group
    codes = []
    for is_fixed, group in grouped_by_variability:
        if is_fixed:
            codes.extend(
                generate_code_for_fixed_fields(
                    group, sourcecode_by_field_name, vectorize
                )
            )
        else:
            codes.append(
                generate_code_for_variable_fields(
                    group, sourcecode_by_field_name
                )
            )

    if generate_for_pack or generate_for_unpack:
        import_code = '''
from struct import pack as StructPack, unpack as StructUnpack
from bisturi.fragments import Fragments
from bisturi.packet import PacketError

'''

    if generate_for_pack:
        pack_code = '''
def pack_impl(pkt, fragments, **k):
%(sync_descriptors_code)s
   k['innermost-pkt-pos'] = fragments.current_offset
   fields = pkt.get_fields()
   try:
%(blocks_of_code)s
   except PacketError as e:
      e.add_parent_field_and_packet(fragments.current_offset, name, pkt.__class__.__name__)
      raise e
   except Exception as e:
      raise PacketError(False, name, pkt.__class__.__name__, fragments.current_offset, str(e))

   return fragments
''' % {
            'blocks_of_code':
            indent("\n".join([c[0] for c in codes]), level=2),
            'sync_descriptors_code':
            generate_unrolled_code_for_descriptor_sync(
                pkt_class, sync_for_pack=True
            ),
        }
    else:
        pack_code = ""

    if generate_for_unpack:
        unpack_code = (
            '''
from struct import pack as StructPack, unpack as StructUnpack
from bisturi.fragments import Fragments
from bisturi.packet import PacketError

def unpack_impl(pkt, raw, offset, **k):
   k['innermost-pkt-pos'] = offset
   fields = pkt.get_fields()
   try:
%(blocks_of_code)s
   except PacketError as e:
      e.add_parent_field_and_packet(offset, name, pkt.__class__.__name__)
      raise e
   except Exception as e:
      raise PacketError(True, name, pkt.__class__.__name__, offset, str(e))

%(sync_descriptors_code)s
   return offset
''' % {
                'blocks_of_code':
                indent("\n".join([c[1] for c in codes]), level=2),
                'sync_descriptors_code':
                generate_unrolled_code_for_descriptor_sync(
                    pkt_class, sync_for_pack=False
                ),
            }
        )
    else:
        unpack_code = ""

    # Compute a hash over the pack and unpack generated code
    # We will use it to verify that the generated code that may already
    # exist correspond with the one generated right now
    cookie_hash = hashlib.sha1()
    cookie_hash.update(pack_code.encode('utf-8'))
    cookie_hash.update(unpack_code.encode('utf-8'))
    cookie = cookie_hash.hexdigest()
    cookie_code = f"BISTURI_PACKET_COOKIE = '{cookie}'\n"

    # From which file we got the packet class?
    try:
        pkt_definition_fpath = inspect.getfile(pkt_class)
    except TypeError:
        # For builtins packet classes (like the ones created in a
        # interactive shell session) will not have a file associated
        # Assume current workign directory as the location for the code
        # generated
        pkt_definition_fpath = './__main__.py'

    pkt_definition_fpath = os.path.abspath(pkt_definition_fpath)

    # We will write the generated code in the same folder
    # that the file above was found, so get its path
    folder = os.path.dirname(pkt_definition_fpath)

    # But put the code in a subfolder named __pkts__
    folder = os.path.join(folder, '__pkts__')

    # Get also the name of the filename (without the extension)
    pkt_definition_module = os.path.splitext(
        os.path.basename(pkt_definition_fpath)
    )[0]

    # Create the new module name based on the original module name
    # and packet class name
    module_name = "%s_%s" % (pkt_definition_module, pkt_class.__name__)

    # Full path for the new module
    module_pathname = os.path.join(folder, module_name + ".py")

    # Try to import it first, if exists
    module = None
    if os.path.exists(module_pathname):
        try:
            module = SourceFileLoader(module_name,
                                      module_pathname).load_module()
        except ImportError:
            pass

    # If no previously written module exists or its cooke does not match
    # ours, recreate the file and reload it
    if not module or getattr(module, 'BISTURI_PACKET_COOKIE', None) != cookie:
        # Delete the compiled file (.pyc)
        if module and hasattr(module, '__cached__'):
            module_compiled_filename = module.__cached__
        else:
            module_compiled_filename = module_name + ".pyc"

        if os.path.exists(module_compiled_filename):
            os.remove(module_compiled_filename)

        # creates folder to host our generated code
        os.makedirs(folder, exist_ok=True)

        with open(module_pathname, 'w') as module_file:
            module_file.write(import_code)
            module_file.write(cookie_code)
            module_file.write(pack_code)
            module_file.write(unpack_code)

        # load it (again)
        module = SourceFileLoader(module_name, module_pathname).load_module()

    from bisturi.packet import Packet
    if generate_for_pack and (pkt_class.pack_impl == Packet.pack_impl):
        pkt_class.pack_impl = module.pack_impl

    if generate_for_unpack and (pkt_class.unpack_impl == Packet.unpack_impl):
        pkt_class.unpack_impl = module.unpack_impl


def generate_unrolled_code_for_descriptor_sync(pkt_class, sync_for_pack):
    if sync_for_pack:
        sync_methods = pkt_class.get_sync_before_pack_methods()
        setup_code = "   sync_methods = pkt.get_sync_before_pack_methods()\n"
    else:
        sync_methods = pkt_class.get_sync_after_unpack_methods()
        setup_code = "   sync_methods = pkt.get_sync_after_unpack_methods()\n"

    if not sync_methods:
        return ""

    sync_calls = '\n'.join('   sync_methods[%i](pkt)' % i \
                                        for i in range(len(sync_methods)))
    return setup_code + sync_calls


def generate_code_for_fixed_fields(
    fields, sourcecode_by_field_name, vectorize
):
    # Group the fields of fixed size by if they have a Python' struct
    # format or not
    grouped_by_has_struct_code = [
        (k, list(g)) for k, g in itertools.
        groupby(fields, lambda i_n_f: i_n_f[2].struct_code is not None)
    ]

    codes = []
    for has_struct_code, group in grouped_by_has_struct_code:
        if has_struct_code:
            if vectorize:
                # We cannot call Python's struct for two fields with different
                # endianness so we do a regroup by fields that have the same
                # endianness in common
                grouped_by_endianness = [
                    (k, list(g)) for k, g in itertools.
                    groupby(group, lambda i_n_f: i_n_f[2].is_bigendian)
                ]

                # Generate the code for each endianness-struct group
                codes.extend(
                    [
                        generate_code_for_fixed_fields_with_struct_code(
                            g, k, sourcecode_by_field_name
                        ) for k, g in grouped_by_endianness
                    ]
                )
            else:
                codes.extend(
                    [
                        generate_code_for_fixed_fields_with_struct_code(
                            [(a, b, f)], f.is_bigendian,
                            sourcecode_by_field_name
                        ) for a, b, f in group
                    ]
                )
        else:
            # Generate the code for each fixed-but-without-struct group
            codes.append(
                generate_code_for_fixed_fields_without_struct_code(
                    group, sourcecode_by_field_name
                )
            )

    return codes


# TODO if is_bigendian  is  None means "don't care",
# no necessary means 'big endian (>)', so it should be joined
# with any other endianness
def generate_code_for_fixed_fields_with_struct_code(
    group, is_bigendian, sourcecode_by_field_name
):
    fmt = ">" if is_bigendian else "<"
    fmt += "".join([f.struct_code for _, _, f in group])

    lookup_fields = " ".join(
        [('pkt.%(name)s,' % {
            'name': name
        }) for _, name, _ in group]
    )

    comments = ''.join(
        sourcecode_by_field_name.get(name, "") for _, name, _ in group
    )

    unpack_code = '''
%(comments)s
name = "%(name)s"
next_offset = offset + %(advance)s
%(lookup_fields)s = StructUnpack("%(fmt)s", raw[offset:next_offset])
offset = next_offset
''' % {
         'comments': comments.rstrip(),
         'lookup_fields': lookup_fields,
         'fmt': fmt,
         'advance': struct.calcsize(fmt),
         'name': ("between '%s' and '%s'" % (group[0][1], group[-1][1])) \
                    if len(group) > 1 else group[0][1],
      }

    pack_code = '''
%(comments)s
name = "%(name)s"
fragments.append(StructPack("%(fmt)s", %(lookup_fields)s))
''' % {
         'comments': comments.rstrip(),
         'lookup_fields': lookup_fields[:-1], # remove the last ","
         'fmt': fmt,
         'name': ("between '%s' and '%s'" % (group[0][1], group[-1][1])) \
                    if len(group) > 1 else group[0][1],
      }

    return pack_code, unpack_code


def generate_code_for_variable_fields(group, sourcecode_by_field_name):
    return (
        generate_code_for_loop_pack(group, sourcecode_by_field_name),
        generate_code_for_loop_unpack(group, sourcecode_by_field_name)
    )


def generate_code_for_fixed_fields_without_struct_code(
    group, sourcecode_by_field_name
):
    return (
        generate_code_for_loop_pack(group, sourcecode_by_field_name),
        generate_code_for_loop_unpack(group, sourcecode_by_field_name)
    )


def generate_code_for_loop_pack(group, sourcecode_by_field_name):
    return ''.join(
        [
            '''
%(comments)s
name, _, pack, _ = fields[%(field_index)i]
pack(pkt=pkt, fragments=fragments, **k)
''' % {
                'comments': sourcecode_by_field_name.get(name, '').rstrip(),
                'field_index': field_index
            } for field_index, name in
            zip(range(group[0][0], group[-1][0] + 1), [g[1] for g in group])
        ]
    )


def generate_code_for_loop_unpack(group, sourcecode_by_field_name):
    return ''.join(
        [
            '''
%(comments)s
name, _, _, unpack = fields[%(field_index)i]
offset = unpack(pkt=pkt, raw=raw, offset=offset, **k)
''' % {
                'comments': sourcecode_by_field_name.get(name, '').rstrip(),
                'field_index': field_index
            } for field_index, name in
            zip(range(group[0][0], group[-1][0] + 1), [g[1] for g in group])
        ]
    )


def indent(code, level=1):
    i = "   " * level
    return "\n".join(
        [((i + line) if line else line) for line in code.split("\n")]
    )
