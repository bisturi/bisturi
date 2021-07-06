# Positions and Alignments

Until now, all our fields in a packet are packed/unpacked sequentially.

This is fine, but in some cases it is desired to control where a field begins.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Ref

>>> class Folder(Packet):
...   offset_of_file = Int(1)
...
...   file_data = Data(4).at(offset_of_file) # TODO is 'absolute' the correct default instead of relative?
```

`at` moves the reading pointer before the field unpacks. This is very
common in file structures where a field says where another field begins.

```python
>>> s = b'\x04XXXABCD'
>>> p = Folder.unpack(s)

>>> p.offset_of_file
4

>>> p.file_data
b'ABCD'

>>> p = Folder(offset_of_file=1)
>>> p.offset_of_file
1

>>> p.file_data
b'\x00\x00\x00\x00'
>>> p.pack()
b'\x01\x00\x00\x00\x00'

>>> p = Folder(offset_of_file=4, file_data=b'ABCD')
>>> p.pack()
b'\x04...ABCD'
```

Note that with `offset_of_file=4` we are saying that the data will start
at that position. If the first byte is the offset, what are the bytes
between them?

By default `bisturi` fills the gaps with just dots.

Moving backward is possible too, even reading the same piece of raw data
already parsed by another field, but at the packing time
you will receive an error.

We can't know how to put two different set of data at the same position!

```python
>>> class Folder(Packet):
...   offset_of_file = Int(1)
...
...   payload   = Data(8)
...   file_data = Data(4).at(offset_of_file)

>>> s = b'\x04XXXABCDX'
>>> p = Folder.unpack(s)

>>> p.offset_of_file
4

>>> p.payload
b'XXXABCDX'

>>> p.file_data
b'ABCD'
```

So good so far, but if we try to pack this...

```python
>>> p.pack()
Traceback (most recent call last):
<...>PacketError: Error when packing the field 'file_data' of packet Folder at 00000004: Collision detected with previous fragment 00000000-00000009 when inserting new fragment at 00000004 that span to 00000008
<...>
```

The problem is that the `file_data` is trying to put its packed data
in the same place where the data of `payload` is already there.

## Relative positions

In other cases we don't want to define an absolute position,
instead we want something relative.

In the following example, we want to start the options field
three bytes after the field `count_options`

```python
>>> class Option(Packet):
...   len = Int(1)
...   data = Data(len)

>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options).at(3, 'relative')
...   checksum = Int(4)

>>> s = b'\x02...\x01A\x04ABCDABCD'
>>> p = Datagram.unpack(s)

>>> p.options[0].data
b'A'
>>> p.options[1].data
b'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True
```

## Alignments

Useful but in general, the most common case is to use a relative position
to align some field.

This is so common that we have a shortcut for that.

```python
>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options).aligned(4)
...   checksum = Int(4)

>>> s = b'\x02...\x01A\x04ABCDABCD'
>>> p = Datagram.unpack(s)

>>> p.options[0].data
b'A'
>>> p.options[1].data
b'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True
```

The alignment was at *field* level: the whole field `options` was aligned.

To align each option in the sequence we do:

```python
>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options, aligned=4)
...   checksum = Int(4)

>>> s = b'\x02...\x01A..\x04ABCDABCD'
>>> p = Datagram.unpack(s)

>>> p.options[0].data
b'A'
>>> p.options[1].data
b'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True
```

It's very common to align all the fields to the same value. As a shortcut we can
resolve this easy:

```python
>>> class Datagram(Packet):
...   __bisturi__ = {'align': 4}
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options)
...   checksum = Int(4)

>>> s = b'\x02...\x01A..\x04ABCD...ABCD'
>>> p = Datagram.unpack(s)

>>> p.options[0].data
b'A'
>>> p.options[1].data
b'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True
```

The alignment is based in the global offset during the packing/unpacking.
For example, if we have this:

```python
>>> class Point(Packet):
...   x = Int(2)    # at position 0
...   y = Int(2).aligned(4) # at position 4

>>> s = b'\x00\x01..\x00\x02'
>>> p = Point.unpack(s)

>>> p.pack() == s
True
```

But if we put this `Point` in another packet, see what happen:

```python
>>> class NamedPoint(Packet):
...   name  = Data(until_marker=b'\0')
...   point = Ref(Point)

>>> s  = b'f\x00\x00\x01\x00\x02'
>>> np = NamedPoint.unpack(s)

>>> np.pack() == s
True
```

Note how the field `point.y` is aligned to 4 without any padding in this case.

This happens because the alignment is global to the full raw data (and
the `name` attribute adds these two extra bytes so `point.y` gets aligned
for free).

In some applications this is what you want but in others don't.

In those cases, you may want to keep the alignment *local* to the packet
begin: the fields are aligned inside the packet but not necessary outside:

```python
>>> class Point(Packet):
...   x = Int(2)
...   y = Int(2).aligned(4, local=True)

>>> s = b'\x00\x01..\x00\x02'
>>> p = Point.unpack(s)

>>> p.x, p.y
(1, 2)

>>> p.pack() == s
True

>>> class NamedPoint(Packet):
...   name  = Data(until_marker=b'\0')
...   point = Ref(Point)

>>> s  = b'f\x00\x00\x01..\x00\x02'
>>> np = NamedPoint.unpack(s)

>>> np.name
b'f'

>>> np.point.x, np.point.y
(1, 2)

>>> np.pack() == s
True
```

In some cases we also want that the whole packet has a size multiple of 4
for example.

We can achieve this adding an extra field at the end and aligning it to 4.

Obviously, this dummy field will not consume any data during the unpacking
and will not introduce any byte during the packing.

```python
>>> from bisturi.field  import Em

>>> class Datagram(Packet):
...   size = Int(1)
...   data = Data(size)
...
...   tail = Em().aligned(4)

>>> # First case, the packet already is multiple of 4
>>> s = b'\x03ABC'
>>> p = Datagram.unpack(s)

>>> p.size
3

>>> p.data
b'ABC'

>>> p.pack() == s
True

>>> # No so lucky this time, we need to add 3 bytes to be multiple of 4
>>> s = b'\x04ABCD...'
>>> p = Datagram.unpack(s)

>>> p.size
4

>>> p.data
b'ABCD'

>>> p.pack() == s
True
```

