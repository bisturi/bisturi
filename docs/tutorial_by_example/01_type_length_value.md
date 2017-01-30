
Bisturi is a library to parse binary data in the less painful way. It's a kind of 'what you see see is what you mean' parser which will allow you to pack and unpack bytes in a declarative way.

Let's see bisturi by the way that he works.
Imagine that your want to parse a classical Type-Length-Value data where Type and Length are integers of 1 and 2 bytes respectively and Value has a 'length' bytes of size.

Let's traduce that description in a packet definition, the way in which you define a parser: 

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data

>>> class TypeLengthValue(Packet):
...     type   = Int(1)
...     length = Int(2)
...     value  = Data(length)

```

As you can see it is quite simple. That's the idea: a simple way to parse without 'writting' parsing code.

Int and Data are what it is called a field, and abstraction that can pack and unpack bytes.
They can accept more arguments to configure them but bisturi tries to pick the most common values as default.

The following is the same packet definition but with all the default arguments made explicit:

```python
>>> class TypeLengthValue(Packet):
...     type   = Int(byte_count=1, signed=False, endianness='big', default=0)
...     length = Int(byte_count=2, signed=False, endianness='big', default=0)
...     value  = Data(byte_count=length, default='')

```

See the reference of Int and Data for more information about those two fields (03_int_field.md, 04_data_field.md)

As said before, bisturi is a library to parse binary data. So what are we waiting for?

```python
>>> raw = '\x09\x00\x04ABCD'
>>> tlv = TypeLengthValue.unpack(raw)

>>> tlv.type
9
>>> tlv.length
4
>>> tlv.value
'ABCD'

```

The object returned by the unpack class method is a packet instance and works like any other python object.
You can change their values:

```python
>>> tlv.type = 2
>>> tlv.type
2

```

and even you can create your own packet instances from the scrach, bisturi will try to use a default value for each field so you don't need to set every single bit:

```python
>>> crafted_tlv = TypeLengthValue(type = 1)
>>> crafted_tlv.type
1
>>> crafted_tlv.length
0
>>> crafted_tlv.value
''

```

Just as you can unpack a byte string into a packet object you can go from a packet object to byte string packing it.

```python
>>> str(tlv.pack())
'\x02\x00\x04ABCD'

>>> str(crafted_tlv.pack())
'\x01\x00\x00'

```

See more about packing and unpacking and the packet objects in 01_simple_packet_creation.md and 02_from_and_to_bytes.md.

