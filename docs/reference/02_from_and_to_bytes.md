# Pack into and Unpack from Bytes

The whole reason of using `bisturi` is to parse some binary
payload into a handy Python object or the other way around,
from Python to a binary payload.

Parsing is know as **unpack** and generating the binary payload
is known as **pack**. If you are familiar with Python's `struct`
library you may recognize the names: we are following the same convention.

## Unpack: from bytes to Python

First, we create a simple packet class as we did before.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)
```

Now, let be the following string of bytes:

```python
>>> s1 = b'\x02\x00\x00\x00\x03abc'
```

Can you see what should be the value of `type` or `payload`?

I hope!. If not, let the packet **dissect the string** for you
calling `unpack`:

```python
>>> p = TLP.unpack(s1)
>>> p.type
2
>>> p.length
3
>>> p.payload
b'abc'
```

`unpack` optionally receives the offset from where to
start reading.

In the following example we would like to ignore the first 3
bytes of `s2` and parse the rest as a `TLP`.

```python
>>> s2 = b'xxx\x01\x00\x00\x00\x01d'
```

Yes, we could do `TLP.unpack(s2[3:])` but that **makes a copy**
-- Python is inflexible here -- and a copy can be somewhat expensive.

Using `offset=` is better:

```python
>>> q = TLP.unpack(s2, offset=3)   #ignore the first 3 bytes "xxx"
>>> q.type
1
>>> q.length
1
>>> q.payload
b'd'
```

### [tl;dr] Field types

Now, if you follow the Python's rules you may ask: *"are the fields
class attributes or instance attributes?"*

They are **instance attributes** so, as you will expect, two packets
may have different values for the same field.

```python
>>> p.type
2
>>> q.type
1
```

Both are different. Under the hood, those object's attributes are optimized
for use low memory and the packets don't have a `__dict__` instance.

```python
>>> hasattr(p, '__dict__')
False
```

## Pack: from Python to bytes

The reverse of `unpack()` is, obviously, `pack()`: it converts a packet into
a sequence of bytes:

```python
>>> p.pack()
b'\x02\x00\x00\x00\x03abc'
```

Ignoring some special cases (not covered here) it is safe to assume that
a packet is *packed into* the same sequence of bytes *from it was
unpacked*:

```python
>>> p.pack() == s1
True
>>> q.pack() == s2[3:]
True
```

## Error handling

Life is never easy and the things not always work as expected: as any
process, `pack()` and `unpack()` may fail.

If a field cannot be unpacked, an exception is raised with the full
stack of packets and offsets:

```python
>>> def some_function(raw):
...    q = TLP.unpack(raw)

>>> s = b'\x00\x00\x00\x00\x04a'

>>> some_function(s)                # byexample: +norm-ws
Traceback (most recent call last):
<...>PacketError: Error when unpacking the field 'payload'
of packet TLP at 00000005: Unpacked 1 bytes but expected 4
Packet stack details:
    00000005 TLP                            .payload
Field's exception:
<...>
Exception: Unpacked 1 bytes but expected 4<...>
```

The exception is telling us that when `bisturi` tried to unpack the
field `payload` of the `TLP` packet it failed.

It was able to unpack 1 byte but expected to unpack 4.

A similar error could happen when packing.

Python is dynamic and `bisturi` does not enforce any type constrain
on the fields attributes.

But when the packet is converted to bytes `bisturi` will make sure
that every field is converted and if something fails it will raise
an exception.

```python
>>> p = TLP()
>>> p.length = "a non integer!"

>>> p.pack()                        # byexample: +norm-ws
Traceback (most recent call last):
<...>PacketError: Error when packing the field 'between 'type' and 'length''
of packet TLP at 00000000: <...> argument <...> integer
Packet stack details:
    00000000 TLP                            .between 'type' and 'length'
Field's exception:
<...>
```

Basically you cannot put apples and expect `bisturi` to make sense
of them. It has not such magic built-in.

`bisturi` **is** capable of packing/unpacking invalid data but that
and more about debugging and errors are for some advanced lecture.

## [extra] Working with files

No always you will have the full string in memory to parse
but you will have a file instead.

`SeekableFile` adapter will make the file behave as a string so
`bisturi` can use it.

```python
>>> from bisturi.util import SeekableFile

>>> seekable_file = SeekableFile(open('tests/ds/tlp_abc', 'rb'))

>>> p = TLP.unpack(seekable_file)
>>> p.length
3
>>> p.payload
b'abc'
```

