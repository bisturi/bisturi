
What are the responsibilities of a `Field`?

Well, it has only one: map back and forward a *"Python object"* to a substring.

Given a string of bytes create from them a *"Python object"*. This is what
`bisturi` calls `unpack`.

The conversion works in the other direction: given a *"Python object"*
return fragments of strings in a operation called `pack`.

This is the only responsibility of each `Field` like `Int`, `Data` and `Ref`.

But what it is this *"Python object"*? This depends of the `Field`,
`bisturi` does not force any interpretation.

For example, `Int` maps a Python `int`, `Data` maps a Python `bytes`
and `Ref` maps a Python object defined by the referenced packet.

Let's create our custom field to handle `gzip` streams to see how you
can create your own fields.

The following example contains a lot of useful information.

```python
>>> from bisturi.field import Field, Data
>>> import zlib

>>> # inherit from Field
>>> class GZip(Field):
...    def __init__(self, byte_count, compress_level=0, default=b'', **k):
...        Field.__init__(self)
...        # Each field must have a default Python object. This may come from
...        # the user but if not, this Field must to provide one.
...        self.default = default
...
...        # You can save any parameter as a field's attribute.
...        # But remember, this is a Field instance, a single instance
...        # for a Packet class, not per Packet instance
...        # In other words, this code will be called *once* per Packet
...        # subclass regardless of how many times you create a packet
...        # instance
...        self.compress_level = compress_level
...
...        # byte_count can be not only an integer but anything like
...        # the name of another field or a callable.
...        # We must use this parameter *only* at the moment of pack/unpack
...        # because only then we can query the value of another field.
...        # You may use byte_count here only if you know that it is not
...        # going to change (like when it is a fixed integer)
...        self.byte_count = byte_count
...
...    def unpack(self, pkt, raw, offset=0, **k):
...        # How many bytes do we need? I will support only two flavours:
...        # the byte_count parameter can be a simple int or it can be
...        # another field. You can extend this to support a callable
...        # or anything else
...        if isinstance(self.byte_count, int):
...            byte_count = self.byte_count
...        else:
...            # This code shows how to get the value of another field
...            # using getattr and the other field's name
...            other_field = self.byte_count
...            byte_count = getattr(pkt, other_field.field_name)
...
...        # Get the compressed data from the raw string of bytes
...        # This code is GZip specific
...        compressed_data = raw[offset:offset+byte_count]
...
...        # Let's unpack this
...        # This code is GZip specific
...        decompressed_data = zlib.decompress(compressed_data)
...
...        # Now we save that as the value of our field into the packet
...        # Remember, the goal of a Field is to set
...        # this attribute during the unpack
...        # Notice how we use setattr and ours field name.
...        # We are *not* doing self.val = val
...        setattr(pkt, self.field_name, decompressed_data)
...
...        # Return the new offset: previous offset
...        # plus how many bytes we consumed
...        return offset + byte_count
...
...    def pack(self, pkt, fragments, **k):
...        # During the pack we need to apply the inverse of unpack
...        # Let's retrieve our decompressed data from the packet instance
...        decompressed_data = getattr(pkt, self.field_name)
...
...        # Get the compress level, self.compress_level it can be
...        # an integer or a field. If it is a field we need to use it
...        # to get the real compress level. If you want you could support a
...        # callable or anything else. I will support only those two options
...        if isinstance(self.compress_level, int):
...            compress_level = self.compress_level
...        else:
...            other_field = self.compress_level
...            compress_level = getattr(pkt, other_field.field_name)
...
...        # Now we compress it
...        # This code is GZip specific
...        compressed_data = zlib.compress(decompressed_data, compress_level)
...
...        # Append the raw string of bytes in the fragments list
...        fragments.append(compressed_data)
...
...        # Finally, we return the fragment list
...        return fragments

```

Let's see a packet definition with this new field

```python
>>> from bisturi.field import Int
>>> from bisturi.packet import Packet

>>> class Compressed(Packet):
...    length = Int(1)
...    level  = Int(1)
...    data   = GZip(byte_count=length, compress_level=level)
```

We can corroborate first that a packet instance's attribute is just a
Python object, in particular `int` for `length` and `level` and `bytes`
for `data` (`bytes` is what `zlib.decompress` returns and it is our
chosen default).

```python
>>> p = Compressed()
>>> isinstance(p.length, Int) # Compressed.length *is* Int but pkt.length *isn't*
False
>>> isinstance(p.length, Field)
False
>>> isinstance(p.length, int) # pkt.length *is* a Python object, not a Field
True

>>> isinstance(p.data, GZip)
False
>>> isinstance(p.data, Field)
False
>>> isinstance(p.data, bytes)
True
```

Let's see the field in action

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
