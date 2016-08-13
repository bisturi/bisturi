FROM_BEGIN = 0
FROM_END   = 2

class SeekableFile(object):
    def __init__(self, file):
        self._file = file
        self._file_length = self._calculate_file_length()

    def __getitem__(self, index):
        if isinstance(index, (int, long)):
            self._seek(index)
            return self._file.read(1)

        elif isinstance(index, slice):
            start, stop, step = index.indices(self._file_length)
            
            if step == 1:
                self._seek(start)
                return self._file.read(stop-start)

            else:
                return "".join((self[i] for i in irange(start, stop, step)))

        else:
            raise TypeError("Invalid index/slice")

    def __str__(self):
        self._seek(0)
        return self._file.read()

    def _seek(self, offset):
        whence = FROM_BEGIN if offset >= 0 else FROM_END
        self._file.seek(offset, whence)

    def _calculate_file_length(self):
        self._file.seek(-1, FROM_END)
        length = self._file.tell() + 1

        self._file.seek(0, FROM_BEGIN)
        return length


def _string_as_seekable_file(s):
    from StringIO import StringIO
    return SeekableFile(file=StringIO(s))


import array
from bisturi.packet import Packet

import string
import binascii
import functools

_non_printable = "".join(map(chr, filter(lambda i: chr(i) not in string.digits + string.letters + string.punctuation + " ", range(256))))
_translate = string.maketrans(_non_printable, len(_non_printable) * ".")
del _non_printable


def inspect(packet, indent="", current_level=0, aligned_to=8, truncate_values_to=8, max_items=4, max_depth=99999):
    inspection_too_deep = current_level > max_depth
    print "%s%s%s" % (indent, packet.__class__.__name__, " [truncated]" if inspection_too_deep else "")

    if inspection_too_deep:
        return

    indent = "  " + indent

    inspect_recursive = functools.partial(inspect, current_level=current_level+1, aligned_to=aligned_to, truncate_values_to=truncate_values_to, max_items=max_items, max_depth=max_depth)
    ALIGNED_TO = aligned_to

    for name, _, _, _ in packet.get_fields():
        value = getattr(packet, name, None)
        indent_and_prefix = "%s%s = " % (indent, name)
 
        space = " " * (ALIGNED_TO - (len(indent_and_prefix) % ALIGNED_TO))

        if isinstance(value, array.array):
            value = value.tostring()

        if isinstance(value, basestring):
            l = len(value)
            MAX = truncate_values_to
            truncated = l > MAX
            truncated_value = value[:MAX]
         
            _value = []
            _value.append(' '.join(x.encode('hex') for x in truncated_value))
            _value.append(" " * ((MAX*3) - len(_value[-1])))
            _value.append("|%s|" % truncated_value.translate(_translate))
            if truncated:
                _value.append("[truncated]")

            _value.append("%i bytes" % l)

            value = "  ".join(_value)
            print "%s%s%s" % (indent_and_prefix, space, value)
        elif isinstance(value, Packet):
            print "%s%s:" % (indent, name)
            inspect_recursive(value, indent)

        elif isinstance(value, (list, tuple)):
            if value:
                truncated = False
                if isinstance(value[0], Packet):
                    truncated = len(value) > max_items
                else:
                    truncated = len(value) > max_items*8

                print "%s%s: %i items %s[" % (indent, name, len(value), "[truncated] " if truncated else "")
                if isinstance(value[0], Packet):
                    for subvalue in value[:max_items]:
                        inspect_recursive(subvalue, indent+"  ")
                    
                else:
                    try:
                        print "%s%s" % (indent+"  ", " ".join(str(v) for v in value[:max_items*8]))
                    except:
                        print "%sunknow values" % (indent + "  ")

                print "%s]" % (indent, )
            else:
                print "%s%s: []" % (indent, name)
        else:
            try:
                try:
                    print "%s%s%s" % (indent_and_prefix, space, value)
                except:
                    value = repr(value)
                    print "%s%s%s" % (indent_and_prefix, space, "unknow '%s'" % value)
            except:
                print "%s%s%s" % (indent_and_prefix, space, "unknow value")

