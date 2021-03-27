
Now, we need to think, what are the responsibilities of one Field? Well, it has only one:
given a string of bytes create from them a 'python object' and given a 'python object'
return fragments of strings.

This is the only responsibility of each Field like Int, Data and Ref.
But what it is this 'python object'? This depends of the Field.

For example, Int can use as its 'python object' an 'int' (and a 'long' for Python 2.x).
The difference between Int and 'int' is that you are almost always interacting with 'int',
the 'python object' of Int and not with the Int itself.

Let's create our custom field to handle gzip streams.

```python
>>> from bisturi.field import Field, Data
>>> import zlib

>>> class GZip(Field):
...    def __init__(self, byte_count, compress_level=0, default='', **k):
...        Field.__init__(self)
...        self.default = default
...
...        # you can save any parameter as a field's parameter
...        # but remember, this is a Field instance, a single instance
...        # for a Packet class, not per Packet instance
...        self.compress_level = compress_level
...
...        # byte_count can be not only an integer but anything like
...        # the name of another field or a callable.
...        # we must use this parameter only at the moment of pack/unpack
...        self.byte_count = byte_count
...
...    def unpack(self, pkt, raw, offset=0, **k):
...        # how many bytes do we need? I will support only two flavours:
...        # the byte_count parameter can be a simple int or it can be
...        # another field. You can extend this to support a callable
...        # or anything else
...        if isinstance(self.byte_count, int):
...            byte_count = self.byte_count
...        else:
...            other_field = self.byte_count
...            byte_count = getattr(pkt, other_field.field_name)
...
...        # get the compressed data from the raw string of bytes
...        compressed_data = raw[offset:offset+byte_count]
...
...        # let's unpack this
...        decompressed_data = zlib.decompress(compressed_data)
...
...        # now we save that as the value of our field into the packet
...        # remember, the objective of a Field is to set
...        # this attribute during the unpack
...        setattr(pkt, self.field_name, decompressed_data)
...
...        # return the new offset: previous offset
...        # plus how many bytes we consumed
...        return offset + byte_count
...
...    def pack(self, pkt, fragments, **k):
...        # during the pack we need to apply the inverse of unpack
...        # let's retreive our decompressed data from the packet instance
...        decompressed_data = getattr(pkt, self.field_name)
...
...        # get the compress level, self.compress_level it can be
...        # an integer or a field. If it is a field we need to use it
...        # to get the real compress level. If you want you could support a
...        # callable or anything else. I will support only those two options
...        if isinstance(self.compress_level, int):
...            compress_level = self.compress_level
...        else:
...            other_field = self.compress_level
...            compress_level = getattr(pkt, other_field.field_name)
...
...        # now we compress it
...        compressed_data = zlib.compress(decompressed_data, compress_level)
...
...        # append the raw string of bytes in the fragments list
...        fragments.append(compressed_data)
...
...        # finally, we return the fragment list
...        return fragments

```

Let's see a packet definition with this new field

```python
>>> from bisturi.field import Int, Field
>>> from bisturi.packet import Packet
>>> class Compressed(Packet):
...    length = Int(1)
...    level  = Int(1)
...    data   = GZip(byte_count=length, compress_level=level)

```

We can corroborate first that a packet instance's attribute is just a
python object

```python
>>> from bisturi.field import Field

>>> p = Compressed()
>>> isinstance(p.length, Int)
False
>>> isinstance(p.length, Field)
False
>>> isinstance(p.length, int)
True

```

Let's see the field in action

```python
```

TODO REVIEW THIS Ok, lets see. 
 - First we inherent from Field. 
 - The constructor __init__ has the expected 'default' keyword and the convenient 'version'.
   With the version as parameter we can handle both version of the IP address schema.
   Two important notes, the parent __init__ is called and the 'default' attribute is setted.
 - Then, the unpack is implemented. We read 4 (or 16) bytes and we set the val interpreted
   using 'setattr'. The new offset is returned (the bytes readed plus the old offset).
   You need to implement the unpack method without assuming the the packet instance (pkt) has
   the field already set. In other words, you cannot call 'getattr' here without calling 'setattr' first.
   You must always return a new instance each time that the unpack is called (or you can return the same
   but if it is inmutable). In this case we are calling 'cls_address' every time.
 - Similar for 'pack'. We get the val using 'getattr' and transform the ip address to
   its binary representation which it is added to the fragments and returned

```python
>>> p = Compressed(data=b'foo')
>>> p.data
b'foo'
>>> p.pack()
b'\x00\x00x\x01\x01\x03\x00\xfc\xfffoo\x02\x82\x01E'

>>> s = b'\x0b\x09x\xdaKJ,\x02\x00\x02]\x016'
>>> p = Compressed.unpack(s)

>>> p.level
9
>>> p.data
b'bar'

>>> p.pack() == s
True

```

Keep this idea. Find some python code that it is useful for you. Then write a small
class to extend Field and thats all!
