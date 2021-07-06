# Bit Fields

So far we saw how to pack/unpack bytes. It is time to go one level deeper
and work with bits:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Bits, Int
>>>
>>> class BitsExample(Packet):
...   fragment_offset = Bits(12)
...   flags = Bits(4)
```

The `Bits` field, as its name suggests, handles a fixed amount of bits
and see them as integers.

In this example, 16 bits are required: 12 bits for `fragment_offset`
and 4 more bits for `flags`.

```python
>>> s = b'\x00\x12'     # which in binary is 0000 0000 0001 0002
>>> p = BitsExample.unpack(s)
>>>
>>> p.fragment_offset   # 'Bits' work with integers like 'Int'
1
>>> p.flags
2

>>> q = BitsExample(fragment_offset=1) # you can set a default as usual
>>> q.flags = 2
>>> q.pack() == s
True
```

## The bytes under the bits

The use of `Bits` has an extra requirement: you can use 1 or more `Bits` fields
but they must be **consecutive** and the sum of the bits must be
**multiple of 8**.

This is because under the hood `bisturi` works at the byte level and
`Bits` are a *front end*, an abstraction on top of them.

The following are some **bad** examples that should illustrate the
possible errors:

```python
>>> # this is wrong because the sum is not multiple of 8
>>> class WrongUse(Packet):
...    fragment_offset = Bits(12)
...    flags = Bits(1)   # 12 + 1 = 13 (not a multiple of 8)
<...>
<...>ByteBoundaryError: Wrong sequence of bits: [12, 1] with total sum of 13 (not a multiple of 8).

>>> # this is wrong because the fields are not consecutive
>>> class WrongUse(Packet):
...    fragment_offset = Bits(9)
...    flags1 = Bits(4)  # bad, because 9 + 4 is not a multiple of 8
...    i = Int()
...    flags3 = Bits(3)   # yes, 12 + 1 + 3 is multiple of 8, but they are not contiguous.
<...>
<...>ByteBoundaryError: Wrong sequence of bits: [9, 4] with total sum of 13 (not a multiple of 8).
```

This however is a **good** example:

```python
>>> # this is fine, consecutive bits sum a multiple of 8
>>> class GoodUse(Packet):
...    fragment_offset = Bits(12)
...    flags1 = Bits(4)  # good because 12 + 4 is a multiple of 8
...    i = Int()
...    flags3 = Bits(4)
...    flags4 = Bits(4)  # good because 4 + 4 is a multiple of 8
```
