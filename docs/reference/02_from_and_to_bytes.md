Now it's time to see how we can create packets from a string and how we can see a packet 
as a string of bytes

First, we create a simple packet class

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)

```

Now, let be the next string of bytes (try to see the values encoded in it)

```python
>>> s1 = '\x02\x00\x00\x00\x03abc'

```

You can see what should be the value of 'type' or 'payload'? 
I hope!. If not, let the packet dissect the string for you using the classmethod 'unpack'

```python
>>> p = TLP.unpack(s1)
>>> p.type
2
>>> p.length
3
>>> p.payload
'abc'

```

And another example

If you need it, you can set the offset of the string where to start to read. Here is another
example

```python
>>> s2 = 'xxx\x01\x00\x00\x00\x01d'
>>> q = TLP.unpack(s2, offset=3)   #ignore the first 3 bytes "xxx"
>>> q.type
1
>>> q.length
1
>>> q.payload
'd'

```

You can see from the class definition that 'type' and the other fields are class's attributes. However the value
of each field is keep per instance, they aren't class's attributes:

```python
>>> p.type
2
>>> q.type
1

```

Both are different. Under the hood, those object's attributes are optimized and saved in the object without
using the __dict__ dictionary of a standar python object:

```
>>> hasattr(p, '__dict__')
False

```

Now, lets do the reverse operation, from the packet to the string of bytes

```python
>>> p.pack() == s1
True
>>> q.pack() == s2[3:]
True

```

If a field cannot be unpacked, an exception is raised with the full stack of packets and offsets:

```python

>>> def some_function(raw):
...    q = TLP.unpack(raw)

>>> s = '\x00\x00\x00\x00\x04a'
>>> some_function(s)                                         #doctest: +ELLIPSIS
Traceback (most recent call last):
...
PacketError: Error when unpacking the field 'payload' of packet TLP at 00000005: Unpacked 1 bytes but expected 4
Packet stack details: 
    00000005 TLP                            .payload
Field's exception:
...
Exception: Unpacked 1 bytes but expected 4...

```

The same is true if the packet cannot be packed into a string:

```python
>>> p = TLP()
>>> p.length = "a non integer!"

>>> p.pack()                                    #doctest: +ELLIPSIS
Traceback (most recent call last):
...
PacketError: Error when packing the field 'between 'type' and 'length'' of packet TLP at 00000000: cannot convert argument to integer
Packet stack details: 
    00000000 TLP                            .between 'type' and 'length'
Field's exception:
...

```

There will be more about debugging, errors and unpacking/packing invalid data but for now we are done.

No always you will have the full string in memory to parse but you will have a file.
Instead of load the full file and read it, you can use the SeekableFile adapter that will
work like a string:

```python
>>> from bisturi.util import SeekableFile
>>>
>>> def _string_as_seekable_file(s):  # used for testing purposes, to fake a real file
...   from StringIO import StringIO
...   return SeekableFile(file=StringIO(s))
>>>
>>> seekable_file = _string_as_seekable_file('\x00\x00\x00\x00\x03abc')

>>> p = TLP.unpack(seekable_file)
>>> p.length
3
>>> p.payload
'abc'

```

