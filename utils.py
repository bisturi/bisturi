import array
from bisturi.packet import Packet 

import string
import binascii

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

   offsets_abs_and_marks = [(1, '\033[32m'), (7, '\033[31m'), (8, '\033[33m'), (0x20, '\033[34m'), (0x38, '\033[35m')]
   last_mark_in_effect = '\033[0m'
   current_pos_for_marks = 0

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

      hex_line   = "%-23s  %-23s" % (" ".join(hex_repr[:8]), " ".join(hex_repr[8:]))
      ascii_line = "%s%s%s"       % (ascii_repr[:8], (" " if len(chunk) > 8 else ""), ascii_repr[8:])

      offsets_rel_and_marks = []
      to_process = offsets_abs_and_marks[current_pos_for_marks:]
      for offset_abs, mark in to_process:
         if offset_abs < offset:
            current_pos_for_marks += 1
            continue
         
         if offset_abs >= offset + 16:
            break

         offsets_rel_and_marks.append((offset_abs-offset, mark))
         current_pos_for_marks += 1

      if not offsets_rel_and_marks:
         offsets_rel_and_marks = [(0, last_mark_in_effect), (16, '\033[0m')]
      else:
         if offsets_rel_and_marks[0][0] != 0:
            offsets_rel_and_marks.insert(0, (0, last_mark_in_effect))

         assert offsets_rel_and_marks[-1][0] != 16

         last_mark_in_effect = offsets_rel_and_marks[-1][1]
         offsets_rel_and_marks.append((16, '\033[0m'))

      hex_line = _xx(hex_line, offsets_rel_and_marks, hex_mode=True)
      ascii_line = _xx(ascii_line, offsets_rel_and_marks, hex_mode=False)
      print "%08x  %s  |%s|" % (offset, hex_line, ascii_line)

   print "%08x" % (offset + 16)


def _xx(line, offsets_rel_and_marks, hex_mode):
   assert offsets_rel_and_marks[0 ][0] == 0
   assert offsets_rel_and_marks[-1][0] == 16

   first_mark = offsets_rel_and_marks[0][1]
   last_position_in_line = 0

   new_line = [first_mark]
   for offset_rel, mark in offsets_rel_and_marks[1:]:
      if hex_mode:
         position_in_line = offset_rel * 3 + (0 if offset_rel < 8 else (1 if offset_rel != 16 else 0))
      else:
         position_in_line = offset_rel * 1 + (0 if offset_rel < 8 else 1)
      
      new_line.append(line[last_position_in_line:position_in_line])
      new_line.append(mark)

      last_position_in_line = position_in_line

   return "".join(new_line)
