Let see the interface of the Int field.
This field represent an integer which can be
 - signed or unsigned
 - represented in bigendian, littleendian or local (based in the local machine, sys.byteorder)

The Int field can require any amount of bytes, 4 by default.
Let see an example

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int

>>> class IntExample(Packet):
...    a = Int()
...    b = Int(1)
...    c = Int(endianness='little')
...    d = Int(1, signed=True)
...    e = Int(endianness='network')
...    f = Int(endianness='local')

```

The code should be self explaining. But to remove any doubt,

```python
>>> a = b'\x00\x00\x00\x01'  # 1
>>> b = b'\x02'              # 2
>>> c = b'\x03\x00\x00\x00'  # 3 in little endian
>>> d = b'\xfc'              # -4
>>> e = b'\x00\x00\x00\x05'  # 5 in big endian (or network order)
>>> f = b'\x00\x00\x00\x06'  # 6 if this machine is big endian, but i don't know.

>>> s = a+b+c+d+e+f
>>> p = IntExample.unpack(s)
>>> [p.a, p.b, p.c, p.d, p.e]
[1, 2, 3, -4, 5]

>>> p.f in (6, 100663296)
True

>>> p.pack() == s
True

```

A little optimization is made when the byte count is fixed and is 1, 2, 4, or 8.
In those cases, the internal implementation uses 'struct'.
But Int can handle other cases, using a hand-crafted implementation. It is slower
 but it is implemented if you need to pack/unpack integers of other non-standar sizes.

```python
>>> class IntExample(Packet):
...    a = Int(3)
...    b = Int(3, endianness='little')
...    c = Int(16, signed=True)
...    d = Int(3, endianness='network')
...    e = Int(3, endianness='local')

>>> a = b'\x00\x00\x01'      # 1
>>> b = b'\x02\x00\x00'      # 2 in little endian
>>> c = b'\xff'*15 + b'\xfd' # -3 (using 16 bytes)
>>> d = b'\x00\x00\x04'      # 4 in big endian (or network order)
>>> e = b'\x00\x00\x05'      # 5 if this machine is big endian, but i don't know.

>>> s = a+b+c+d+e
>>> p = IntExample.unpack(s)
>>> [p.a, p.b, int(p.c), p.d]
[1, 2, -3, 4]

>>> p.e in (5, 327680)
True

>>> p.pack() == s
True

```

To see the 'cost' of both implementations, we can mount a very rudimentary test.

```python
>>> import timeit
>>> class IntOptimized(Packet):
...    a = Int(4)
...    b = Int(4)
>>>
>>> class IntGeneral(Packet):
...    a = Int(3)
...    b = Int(5)
>>> 
>>> s = b'\x00\xff\x00\x00\x00\x00\xff\x00'
>>> topt = timeit.Timer(lambda: IntOptimized.unpack(s))
>>> tgen = timeit.Timer(lambda: IntGeneral.unpack(s))
>>>
>>> best_topt = min(topt.repeat(repeat=10, number=1000))
>>> best_tgen = min(tgen.repeat(repeat=10, number=1000))

>>> best_topt < best_tgen
True

```

In some cases you need to change the endianness of all the Ints from big endian (default)
to little endian.
Changeing this in each Int is terrible, so we can change the default policy directly 

```python

>>> class IntWithDifferentDefault(Packet):
...    __bisturi__ = {'endianness': 'little'}
...
...    a = Int(2, endianness='little')
...    b = Int(2)    # now, littleendian by default
...    c = Int(2, endianness='network')

>>> a = b'\x01\x00'          # 1 in little endian
>>> b = b'\x02\x00'          # 2 in little endian too
>>> c = b'\x00\x03'          # 3 in big endian (or network order)

>>> s = a+b+c
>>> p = IntWithDifferentDefault.unpack(s)
>>> [p.a, p.b, p.c]
[1, 2, 3]

>>> p.pack() == s
True

```

