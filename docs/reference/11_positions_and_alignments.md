Until now, all our fields in a packet are packed/unpacked sequentially.
This is fine, but in some cases it is desired to control where a field begins.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int 

>>> class Folder(Packet):
...   offset_of_file = Int(1)
...
...   file_data = Data(4).at(offset_of_file) # TODO revisar el default de esto

```


```python
>>> s = '\x04XXXABCD'
>>> p = Folder(s)

>>> p.offset_of_file
4

>>> p.file_data
'ABCD'

```

```python
>>> p = Folder(offset_of_file=1)

>>> p.offset_of_file
1

>>> p.file_data
'\x00\x00\x00\x00'
>>> str(p.pack())
'\x01\x00\x00\x00\x00'

>>> p = Folder(offset_of_file=4, file_data='ABCD')
>>> str(p.pack())
'\x04...ABCD'

```

Note that moving to back is possible too, even reading the same piece of raw data 
already parsed by another field, but at the packing time you will receive an error.
We can't know how to put two diferent set of data at the same position!

```python

>>> class Folder(Packet):
...   offset_of_file = Int(1)
...   
...   payload   = Data(8)
...   file_data = Data(4).at(offset_of_file) # TODO revisar el default de esto

```

```python
>>> s = '\x04XXXABCDX'
>>> p = Folder(s)

>>> p.offset_of_file
4

>>> p.payload
'XXXABCDX'

>>> p.file_data
'ABCD'

```

So good so far, but if we try to pack this...

```python
### p = Folder(offset_of_file=4, file_data='ABCD')

### p.offset_of_file
4
### p.payload
'\x00\x00\x00\x00\x00\x00\x00\x00'

### p.file_data
'ABCD'

>>> p.pack()                                # doctest: +ELLIPSIS
Traceback (most recent call last):
Exception: Error when packing field 'file_data' of packet Folder at 00000004...Collision detected with previous fragment 00000...-00000009...

```

The problem is that the file_data is trying to put its packed data in the same place where the data of payload is already there.
For that reason we get an exception.

Relative positions
------------------

In other cases we dont want to define an absolute position, instead we want something
relative.

In the following example, we want to start the options field three bytes after the
field count_options

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Ref

>>> class Option(Packet):
...   len = Int(1)
...   data = Data(len)

>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options).at(3, 'relative')
...   checksum = Int(4)

>>> s = '\x02...\x01A\x04ABCDABCD'
>>> p = Datagram(s)

>>> p.options[0].data
'A'
>>> p.options[1].data
'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True

```

Alignements
-----------

Useful but in general, the most common case is to use a relative position to align
some field. This is so common that we have a shortcut for that.
If we want that the options field be alinged to 4 byte we do:

```python
>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options).aligned(4)
...   checksum = Int(4)

>>> s = '\x02...\x01A\x04ABCDABCD'
>>> p = Datagram(s)

>>> p.options[0].data
'A'
>>> p.options[1].data
'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True

```

The alignement was at 'field' level: the whole fielf 'options' was aligned.
To align each option in the sequence we do:

```python
>>> class Datagram(Packet):
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options, aligned=4)
...   checksum = Int(4)

>>> s = '\x02...\x01A..\x04ABCDABCD'
>>> p = Datagram(s)

>>> p.options[0].data
'A'
>>> p.options[1].data
'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True

```

It's very common to align all the fields to the same value. As a shortcut we can
resolve this easly:

```python
>>> class Datagram(Packet):
...   __bisturi__ = {'align': 4}
...   count_options = Int(1)
...   options = Ref(Option).repeated(count_options)
...   checksum = Int(4)

>>> s = '\x02...\x01A..\x04ABCD...ABCD'
>>> p = Datagram(s)

>>> p.options[0].data
'A'
>>> p.options[1].data
'ABCD'
>>> p.checksum == 0x41424344
True

>>> p.pack() == s
True

```

In some cases we also want that the whole packet has a size multiple of 4 for example.
We can achieve this adding an extra field an the end and aligning it to 4.
Obviously, this dummy field will not consume any data during the unpacking neither
will introduce any byte during the packing.

```python
>>> from bisturi.field  import Em, Bkpt

>>> class Datagram(Packet):
...   __bisturi__ = {'generate_for_pack': False}
...   size = Int(1)
...   data = Data(size)
...
...   tail = Em().aligned(4)

>>> # First case, the packet already is multiple of 4
>>> s = '\x03ABC'
>>> p = Datagram(s)

>>> p.size
3

>>> p.data
'ABC'

>>> p.pack() == s
True

>>> # No so lucky this time, we need to add 3 bytes to be multiple of 4
>>> s = '\x04ABCD...'
>>> p = Datagram(s)

>>> p.size
4

>>> p.data
'ABCD'

>>> p.pack() == s
True


```
