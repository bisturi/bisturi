Some times, the field use a partial count of bytes. Only a few bits are used.


>>> from packet import Packet
>>> from field  import Bits, Int
>>>
>>> class BitsExample(Packet):
...   fragment_offset = Bits(12)
...   flags = Bits(4)

In this example, 2 bytes are required but the distribution of th bits is not 8,8.
As you can see, it is 12,4.
The default interpretation of the field is like an integer.

>>> s = '\x00\x12'
>>> p = BitsExample(s)
>>>
>>> p.fragment_offset
1
>>> p.flags
2

>>> q = BitsExample(fragment_offset=1)
>>> q.flags = 2
>>> q.pack() == s
True

The implementation require that the sequence of Bits field consume an entire byte 
(or a multiple). So, the sumatory of bits must be a multiple of 8.
Partial usages are not allowed.

>>> try:
...   class WrongUse(Packet):
...     fragment_offset = Bits(12)
...     flags = Bits(1)   # 12 + 1 = 13 (not a multiple of 8)
... except Bits.ByteBoundaryError:
...   True
True

This restriction is needed for each contiguous sequence

>>> try:
...   class WrongUse(Packet):
...     fragment_offset = Bits(12)   # the sequence is fragment_offset and flags1
...     flags1 = Bits(1)  # so, because 12 + 1 is not a multiple of 8, this is wrong
...     i = Int()
...     flags3 = Bits(3)   # yes, 12 + 1 + 3 is multiple of 8, but they are not contiguous.
... except Bits.ByteBoundaryError:
...   True
True

