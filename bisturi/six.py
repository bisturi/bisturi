import sys

try:
    integer_types = (int, long)
except NameError:
    integer_types = (int, )

if sys.version_info[0] == 2:
    text_types = (unicode,)
else:
    text_types = (str,)


if sys.version_info[0] == 2:
    from_int_to_byte = chr
else:
    def from_int_to_byte(i):
        return bytes([i])


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

    try:
        return type.__new__(metaclass, u'temporary_class', (), {})
    except TypeError:
        return type.__new__(metaclass, b'temporary_class', (), {})
