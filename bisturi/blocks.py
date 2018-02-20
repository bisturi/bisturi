from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import struct
import itertools
import hashlib
import os.path
import imp

def generate_code(fields, pkt_class, generate_for_pack, generate_for_unpack,
                                                            write_py_module):
    if not generate_for_pack and not generate_for_unpack:
        return

    grouped_by_variability = [(k, list(g)) for k, g in itertools.groupby(fields, lambda i_n_f: i_n_f[2].is_fixed)]
    codes = []
    for is_fixed, group in grouped_by_variability:
        if is_fixed:
            codes.extend(generate_code_for_fixed_fields(group))
        else:
            codes.append(generate_code_for_variable_fields(group))
    if generate_for_pack or generate_for_unpack:
        import_code = '''
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from struct import pack as StructPack, unpack as StructUnpack
from bisturi.fragments import Fragments
from bisturi.packet import PacketError

'''
    if generate_for_pack:
        pack_code = '''
def pack_impl(pkt, fragments, **k):
%(sync_descriptors_code)s
   k['local_offset'] = fragments.current_offset
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
      'blocks_of_code': indent("\n".join([c[0] for c in codes]), level=2),
      'sync_descriptors_code': generate_unrolled_code_for_descriptor_sync(
                                                pkt_class, sync_for_pack=True),
    }
    else:
        pack_code = ""

    if generate_for_unpack:
        unpack_code = ('''
from struct import pack as StructPack, unpack as StructUnpack
from bisturi.fragments import Fragments
from bisturi.packet import PacketError

def unpack_impl(pkt, raw, offset, **k):
   k['local_offset'] = offset
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
      'blocks_of_code': indent("\n".join([c[1] for c in codes]), level=2),
      'sync_descriptors_code': generate_unrolled_code_for_descriptor_sync(pkt_class, sync_for_pack=False),
    })
    else:
        unpack_code = ""

    cookie_hash = hashlib.sha1()
    cookie_hash.update(pack_code.encode('utf-8'))
    cookie_hash.update(unpack_code.encode('utf-8'))
    cookie = cookie_hash.hexdigest()
    cookie_code = "BISTURI_PACKET_COOKIE = '%(cookie)s'\n" % {
      'cookie': cookie,
    }

    module_name = "_%s_pkt" % pkt_class.__name__
    module_filename = module_name + ".py"

    module = None
    if os.path.exists(module_filename):
        try:
            module = imp.load_source(module_name, module_filename)
        except ImportError:
            pass

    if module and hasattr(module, '__cached__'):
        module_compiled_filename = module.__cached__
    else:
        module_compiled_filename = module_name + ".pyc"

    if not module or getattr(module, 'BISTURI_PACKET_COOKIE', None) != cookie:
        if os.path.exists(module_compiled_filename):
            os.remove(module_compiled_filename)

        with open(module_filename, 'w') as module_file:
            module_file.write(import_code)
            module_file.write(cookie_code)
            module_file.write(pack_code)
            module_file.write(unpack_code)

        module = imp.load_source(module_name, module_filename)

        if module and hasattr(module, '__cached__'):
            module_compiled_filename = module.__cached__
        else:
            module_compiled_filename = module_name + ".pyc"

        if not write_py_module:
            try:
                os.remove(module_compiled_filename)
            except:
                pass
            os.remove(module_filename)

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
        return "   "

    sync_calls = '\n'.join('   sync_methods[%i](pkt)' % i \
                                        for i in range(len(sync_methods)))
    return setup_code + sync_calls


def generate_code_for_fixed_fields(fields):
    grouped_by_struct_code =  [(k, list(g)) for k, g in \
                                itertools.groupby(fields,
                                                  lambda i_n_f: i_n_f[2].struct_code is not None)]
    codes = []
    for has_struct_code, group in grouped_by_struct_code:
        if has_struct_code:
            grouped_by_endianness = [(k, list(g)) for k, g in \
                                        itertools.groupby(group,
                                                        lambda i_n_f: i_n_f[2].is_bigendian)]

            codes.extend([generate_code_for_fixed_fields_with_struct_code(g, k) \
                                for k, g in grouped_by_endianness])
        else:
            codes.append(generate_code_for_fixed_fields_without_struct_code(group))

    return codes

# TODO if is_bigendian  is  None means "don't care",
# no necessary means 'big endian (>)', so it should be joined
# with any other endianness
def generate_code_for_fixed_fields_with_struct_code(group, is_bigendian):
    fmt = ">" if is_bigendian else "<"
    fmt += "".join([f.struct_code for _, _, f in group])

    lookup_fields = " ".join([('pkt.%(name)s,' % {'name': name}) for _, name, _ in group])
    unpack_code = '''
name = "%(name)s"
next_offset = offset + %(advance)s
%(lookup_fields)s = StructUnpack("%(fmt)s", raw[offset:next_offset])
offset = next_offset
''' % {
         'lookup_fields': lookup_fields,
         'fmt': fmt,
         'advance': struct.calcsize(fmt),
         'name': ("between '%s' and '%s'" % (group[0][1], group[-1][1])) \
                    if len(group) > 1 else group[0][1],
      }

    pack_code = '''
name = "%(name)s"
fragments.append(StructPack("%(fmt)s", %(lookup_fields)s))
''' % {
         'lookup_fields': lookup_fields[:-1], # remove the last ","
         'fmt': fmt,
         'name': ("between '%s' and '%s'" % (group[0][1], group[-1][1])) \
                    if len(group) > 1 else group[0][1],
      }

    return pack_code, unpack_code

def generate_code_for_variable_fields(group):
    return (generate_code_for_loop_pack(group), generate_code_for_loop_unpack(group))

def generate_code_for_fixed_fields_without_struct_code(group):
    return (generate_code_for_loop_pack(group), generate_code_for_loop_unpack(group))

def generate_code_for_loop_pack(group):
    return ''.join(['''
name, _, pack, _ = fields[%(field_index)i]
pack(pkt=pkt, fragments=fragments, **k)
''' % {
      'field_index': field_index
   } for field_index in range(group[0][0], group[-1][0]+1)])

def generate_code_for_loop_unpack(group):
    return ''.join(['''
name, _, _, unpack = fields[%(field_index)i]
offset = unpack(pkt=pkt, raw=raw, offset=offset, **k)
''' % {
      'field_index': field_index
   } for field_index in range(group[0][0], group[-1][0]+1)])


def indent(code, level=1):
    i = "   " * level
    return "\n".join([i + line for line in code.split("\n")])

