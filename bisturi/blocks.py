import struct
import itertools
import hashlib
import os.path
import imp

def generate_code(fields, pkt_class, generate_for_pack, generate_for_unpack, write_py_module):
   if not generate_for_pack and not generate_for_unpack:
      return

   grouped_by_variability = [(k, list(g)) for k, g in itertools.groupby(fields, lambda i_n_f: i_n_f[2].is_fixed)]
   codes = []
   for is_fixed, group in grouped_by_variability:
      if is_fixed:
         codes.extend(generate_code_for_fixed_fields(group))
      else:
         codes.append(generate_code_for_variable_fields(group))

   if generate_for_pack:
      pack_code = '''
from struct import pack as StructPack, unpack as StructUnpack
def pack(pkt, **k):
   chunks_raw = []
%(blocks_of_code)s

   return "".join(chunks_raw)
''' % {
      'blocks_of_code': indent("\n".join([c[0] for c in codes]))
   }
   else:
      pack_code = ""

   if generate_for_unpack:
      unpack_code = ('''
from struct import pack as StructPack, unpack as StructUnpack
def unpack(pkt, raw, offset=0, stack=None, **k):
   stack = pkt.push_to_the_stack(stack)
   try:
%(blocks_of_code)s
   except Exception, e:
%(except_block)s
   pkt.pop_from_the_stack(stack)
   return offset
''' % {
      'blocks_of_code': indent("\n".join([c[1] for c in codes]), level=2),
      'except_block': indent('''
import traceback
msg = traceback.format_exc()
raise Exception("Error when parsing field '%s' of packet %s at %08x: %s" % (
                              name, pkt.__class__.__name__, offset, msg))
''', level=2)
   })
   else:
      unpack_code = ""

   cookie_hash = hashlib.sha1()
   cookie_hash.update(pack_code)
   cookie_hash.update(unpack_code)
   cookie = cookie_hash.hexdigest()
   cookie_code = "BISTURI_PACKET_COOKIE = '%(cookie)s'\n" % {
      'cookie': cookie,
   }

   module_name = "_%s_pkt" % pkt_class.__name__
   module_filename = module_name + ".py"
   module_compiled_filename = module_name + ".pyc"

   module = None
   if os.path.exists(module_filename) or os.path.exists(module_compiled_filename):
      try:
         module = imp.load_source(module_name, module_filename)
      except ImportError:
         pass


   if not module or getattr(module, 'BISTURI_PACKET_COOKIE', None) != cookie:
      if os.path.exists(module_compiled_filename):
         os.remove(module_compiled_filename)

      with open(module_filename, 'w') as module_file:
         module_file.write(cookie_code)
         module_file.write(pack_code)
         module_file.write(unpack_code)

      module = imp.load_source(module_name, module_filename)
      if not write_py_module:
         os.remove(module_compiled_filename)
         os.remove(module_filename)
 
   if generate_for_pack:  
      pkt_class.pack = module.pack

   if generate_for_unpack:
      pkt_class.unpack = module.unpack
            

def generate_code_for_fixed_fields(fields):
   grouped_by_struct_code =  [(k, list(g)) for k, g in itertools.groupby(fields, lambda i_n_f: i_n_f[2].struct_code is not None)]
   codes = []
   for has_struct_code, group in grouped_by_struct_code:
      if has_struct_code:
         grouped_by_endianess = [(k, list(g)) for k, g in itertools.groupby(group, lambda i_n_f: i_n_f[2].is_bigendian)]
         codes.extend([generate_code_for_fixed_fields_with_struct_code(g, k) for k, g in grouped_by_endianess])
      else:
         codes.append(generate_code_for_fixed_fields_without_struct_code(group))

   return codes

# TODO if is_bigendian  is  None means "don't care", no necessary means 'big endian (>)', so it should be joined with any other endianess
def generate_code_for_fixed_fields_with_struct_code(group, is_bigendian):
   fmt = ">" if is_bigendian else "<"
   fmt += "".join([f.struct_code for _, _, f in group])

   lookup_fields  = " ".join([('pkt.%(name)s,' % {'name': name}) for _, name, _ in group])
   unpack_code = '''
try:
   next_offset = offset + %(advance)s
   %(lookup_fields)s = StructUnpack("%(fmt)s", raw[offset:next_offset])
   offset = next_offset
except Exception, e:
   print e
%(loop_for_unpack)s
''' % {
         'lookup_fields': lookup_fields,
         'fmt': fmt,
         'advance': struct.calcsize(fmt),
         'loop_for_unpack': indent(generate_code_for_loop_unpack(group))
      }

   pack_code = '''
try:
   chunks_raw.append(StructPack("%(fmt)s", %(lookup_fields)s))
except:
%(loop_for_pack)s
''' % {
         'lookup_fields': lookup_fields[:-1], # remove the last ","
         'fmt': fmt,
         'loop_for_pack': indent(generate_code_for_loop_pack(group))
      }
   
   return pack_code, unpack_code

def generate_code_for_variable_fields(group):
   return (generate_code_for_loop_pack(group), generate_code_for_loop_unpack(group))

def generate_code_for_fixed_fields_without_struct_code(group):
   return (generate_code_for_loop_pack(group), generate_code_for_loop_unpack(group))

def generate_code_for_loop_pack(group):
   return '''
chunks_raw.extend([f.pack(pkt) for name, f in pkt.get_fields()[%(start_index)i:%(end_index)i]])
''' % {
         'start_index': group[0][0],
         'end_index':   group[-1][0]+1,
      }

def generate_code_for_loop_unpack(group):
   return '''
for name, f in pkt.get_fields()[%(start_index)i:%(end_index)i]:
   offset = f.unpack(pkt=pkt, raw=raw, offset=offset, stack=stack, **k)
''' % {
         'start_index': group[0][0],
         'end_index':   group[-1][0]+1,
      }

def indent(code, level=1):
   i = "   " * level
   return "\n".join([i + line for line in code.split("\n")])