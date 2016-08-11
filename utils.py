import array
from bisturi.packet import Packet 

import string

_non_printable = "".join(map(chr, filter(lambda i: chr(i) not in string.digits + string.letters + string.punctuation + " ", range(256))))
_translate = string.maketrans(_non_printable, len(_non_printable) * ".")
del _non_printable

def inspect(packet, indent=""):
   print "%s%s" % (indent, packet.__class__.__name__)
   print "%s%s" % (indent, "=" * len(packet.__class__.__name__))
   for name, _ in packet.get_fields():
      value = getattr(packet, name)
      if isinstance(value, array.array):
         value = value.tostring()

      if isinstance(value, basestring):
         value = ':'.join(x.encode('hex') for x in value)

      if isinstance(value, Packet):
         print "%s%s:" % (indent, name)
         inspect(value, indent+"  ")
         value = None

      if isinstance(value, (list, tuple)):
         if value:
            print "%s%s: [" % (indent, name)
            for subvalue in value:
               inspect(subvalue, indent+"  ")
            print "%s]" % (indent, )
         else:
            print "%s%s: []" % (indent, name)

         value = None

      if value is not None:
         print "%s%s = %s" % (indent, name, value)

def hd(raw, full=False):
   last_chunk = ""
   ignoring = False

   for offset in range(0, len(raw), 16):
      chunk = raw[offset : offset+16]
      if not full and last_chunk == chunk:
         if not ignoring:
            print "*"
            ignoring = True

         continue
      else:
         ignoring = False
         last_chunk = chunk

      hd = binascii.b2a_hex(chunk)

      hex_repr = ([hd[i: i+2] for i in range(0, 32, 2)])
      ascii_repr = chunk.translate(_translate)

      print "%08x  %-23s  %-23s  |%s%s%s|" % (offset, " ".join(hex_repr[:8]), " ".join(hex_repr[8:]), ascii_repr[:8], (" " if len(chunk) > 8 else ""), ascii_repr[8:])

   print "%08x" % (offset + 16)
