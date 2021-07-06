# Integer Fields

A `Int` field represents an integer which can:

 - be signed or unsigned.
 - be in big endian, little endian or local endian
(based in the local machine, `sys.byteorder`)
 - be of arbitrary but fixed size.

By default `Int` represents an unsigned, big endian integer of 4 bytes
but that can be changed of course.

Let see an example that uses several different `Int`s

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

The code should be self explanatory, but to remove any doubt:

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

>>> p.f in (6, 100663296) # it can be little or big endian
True

>>> p.pack() == s
True
```

### [extra] Arbitrary fixed size

`Int` supports an arbitrary number of bytes as its size but it is
**heavily optimized** for fixed sizes of 1, 2, 4 and 8.

In this other example we have `Int`s of non-standard sizes and `bisturi`
works just fine.

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

## Change defaults per packet

In some cases your packets are described more naturally in little endian.

Instead of changing this in each `Int` field, you can change the default
per packet class:

```python
>>> class IntWithDifferentDefault(Packet):
...    __bisturi__ = {'endianness': 'little'}
...
...    a = Int(2, endianness='little')
...    b = Int(2)    # now, little endian by default
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

`__bisturi__` is a special attribute that controls several aspects of
`Packet`. For now it is sufficient to say that
with `{'endianness': ...}` you can control the defaults for that packet class.
