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
         l = len(value)
         truncated = l > 16
         
         _value = []
         _value.append(' '.join(x.encode('hex') for x in value[:16]))
         _value.append("|%s|" % value[:16].translate(_translate))
         if truncated:
            _value.append("[truncated]")

         _value.append("%i bytes" % l)

         value = "  ".join(_value)

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

import termcolor

def mark_with_color(color, attr=None, bg=None):
   fmt = '\033[%im'
   codes = [0, termcolor.COLORS[color]]

   if bg:
      codes.append(termcolor.HIGHLIGHTS[bg])

   if attr:
      codes.append(termcolor.ATTRIBUTES[attr])

   return "".join([fmt % code for code in codes])

import bisturi.field as F
def xx(raw, packet, offset=0):
   colours_by_class = {
      F.Int:  [mark_with_color('red'),   mark_with_color('red', 'bold')],
      F.Bits: [mark_with_color('yellow'),  mark_with_color('yellow')],
      F.Data: [mark_with_color('magenta'), mark_with_color('magenta', 'bold')],
      F.Ref:  [mark_with_color('cyan'),    mark_with_color('cyan', 'bold')],
      None: [mark_with_color('green'),    mark_with_color('green', 'bold')],
      F.Sequence: [mark_with_color('cyan'),    mark_with_color('cyan', 'bold')],
      }

   for k in colours_by_class.keys():
      if k is None:
         k_name = "<default>" 
      else:
         k_name = k.__name__
      print "%s%s %s%s" % (colours_by_class[k][0], k_name, colours_by_class[k][1], k_name)

   print '\033[0m'

   it = packet.iterative_unpack(raw, offset)
   current_offset, field_name = next(it)
   marks = []
   last_cls = None
   times = -1
   try:
      while field_name != ".":
         marks.append((current_offset, '\033[0m'))
         tmp = next(it)
         #print ("%08x  %s = %s" % (current_offset, field_name, getattr(packet, field_name)))
         
         mro = getattr(packet.__class__, field_name).__class__.mro()
         cls = None
         for F in colours_by_class.keys():
            if F in mro:
               cls = F
               break
         
         if cls == last_cls:
            times += 1
         else:
            times = 0
            last_cls = cls

         colour = colours_by_class[cls][times % 2]

         marks.append((current_offset, colour))
         current_offset, field_name = tmp
      
      #print "%08x" % current_offset
      marks.append((current_offset, '\033[0m'))
      it.close()
   finally:
      #hd(raw)
      hd(raw, full=True, offsets_abs_and_marks=marks)
      inspect(packet)

def hd(raw, full=False, offsets_abs_and_marks=[]):
   last_chunk = ""
   ignoring = False

   #offsets_abs_and_marks = [(1, '\033[32m'), (7, '\033[31m'), (8, '\033[33m'), (0x20, '\033[34m'), (0x38, '\033[35m')]
   last_mark_in_effect = '\033[0m'
   current_pos_for_marks = 0

   offset = 0
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
