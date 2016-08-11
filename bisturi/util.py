
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

