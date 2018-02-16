from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from bisturi.six import integer_types

FROM_BEGIN = 0
FROM_END   = 2

def to_bytes(bytes_or_text):
    return (bytes_or_text if isinstance(bytes_or_text, bytes)
                          else bytes(bytes_or_text, 'ascii'))

class SeekableFile(bytes):
    def __new__(cls, file_open):
        self = bytes.__new__(cls)

        self._file = file_open
        self._file_length = self._calculate_file_length()

        return self

    def __getslice__(self, i, j):
        # deprecated, but still necessary to redefine the behavior of 'bytes'
        return self._slice(slice(i, j))

    def __getitem__(self, index):
        if isinstance(index, integer_types):
            self._seek(index)
            return self._file.read(1)

        elif isinstance(index, slice):
            return self._slice(index)

        else:
            raise TypeError("Invalid index/slice")

    def _slice(self, index):
        start, stop, step = index.indices(self._file_length)

        if step == 1:
            self._seek(start)
            return self._file.read(stop-start)

        else:
            return b"".join((self[i] for i in irange(start, stop, step)))

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
    return SeekableFile(file_open=StringIO(s))


import array
from bisturi.packet import Packet

import string
import binascii
import functools

_non_printable = set(range(256)) - set(ord(c) for c in string.printable)
_non_printable.union(ord(c) for c in string.whitespace if c != ' ')
_translate = ''.join('.' if i in _non_printable else chr(i) for i in range(256))
del _non_printable

def inspect(packet, indent="", current_level=0, aligned_to=8,
                truncate_values_to=8, max_items=4, max_depth=99999):
    inspection_too_deep = current_level > max_depth
    print("%s%s%s" % (indent, packet.__class__.__name__, " [truncated]"
                            if inspection_too_deep
                            else ""))

    if inspection_too_deep:
        return

    indent = "  " + indent

    inspect_recursive = functools.partial(inspect, current_level=current_level+1,
                                                   aligned_to=aligned_to,
                                                   truncate_values_to=truncate_values_to,
                                                   max_items=max_items,
                                                   max_depth=max_depth)
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
            print("%s%s%s" % (indent_and_prefix, space, value))
        elif isinstance(value, Packet):
            print("%s%s:" % (indent, name))
            inspect_recursive(value, indent)

        elif isinstance(value, (list, tuple)):
            if value:
                truncated = False
                if isinstance(value[0], Packet):
                    truncated = len(value) > max_items
                else:
                    truncated = len(value) > max_items*8

                print("%s%s: %i items %s[" % \
                        (indent, name, len(value),
                        "[truncated] " if truncated else ""))
                if isinstance(value[0], Packet):
                    for subvalue in value[:max_items]:
                        inspect_recursive(subvalue, indent+"  ")

                else:
                    try:
                        print("%s%s" % \
                                (indent+"  ",
                                 " ".join(str(v) for v in value[:max_items*8])))
                    except:
                        print("%sunknow values" % (indent + "  "))

                print("%s]" % (indent, ))
            else:
                print("%s%s: []" % (indent, name))
        else:
            try:
                try:
                    print("%s%s%s" % (indent_and_prefix, space, valuea))
                except:
                    value = repr(value)
                    print("%s%s%s" % \
                            (indent_and_prefix, space, "unknow '%s'" % value))
            except:
                print("%s%s%s" % (indent_and_prefix, space, "unknow value"))

