bisturi
=======

Bisturi is a library to parse binary data in the less painful way: no need to write 'for' loops neither nested 'if' conditionals. It's a kind of 'what you see see is what you mean' parser which will allow you to pack and unpack bytes in a declarative way.

Let's see bisturi by examples.

This is the classical Type-Length-Value packet and how we can describe it in bisturi.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data

>>> class TypeLengthValue(Packet):
...     type   = Int(1)
...     length = Int(2)
...     value  = Data(length)

```

From the source it's easy to see that the type is an integer of 1 byte meanwhile the length is an integer of size 2.
The value is a data of variable size of length bytes.

That's all what you need. The principal objective of bisturi is to allow you to write simple classes easy to read and understand hidding almost everything parsing details behind the scene.

After the packet definition you can parse any byte string in one call:

```python
>>> raw = '\t\x00\x04ABCD'
>>> tlv = TypeLengthValue.unpack(raw)

>>> tlv.type
9
>>> tlv.length
4
>>> tlv.value
'ABCD'

```

As well you can parse (unpack) a byte string you can do the reverse, pack a packet into a byte string:

```python
>>> str(tlv.pack())
'\t\x00\x04ABCD'

```

Int and Data are not the only fields available. 
Here is an example of how to describe a bit mask

```python
>>> from bisturi.field  import Bits

>>> class FrameControl(Packet):
...     length = Bits(6)
...     more_fragments = Bits(1)
...     fragment_offset = Bits(9)
...     data = Data(length)

>>> raw = '\x0c\x05abc'
>>> fc = FrameControl.unpack(raw)

>>> fc.length
3
>>> fc.more_fragments
0
>>> fc.fragment_offset
5
>>> fc.data
'abc'

```

And here is how to describe a sequence of values (aka list) and an optional field:

```python
>>> class Image1D(Packet):
...     has_name = Bits(1)
...     count_numbers = Bits(7)
...
...     numbers = Int(1).repeated(count_numbers)
...     optional_name = Data(until_marker='\x00').when(has_name)

>>> raw_without_name = '\x03ABC'
>>> image1d = Image1D.unpack(raw_without_name)

>>> image1d.has_name
0
>>> image1d.count_numbers
3
>>> image1d.numbers
[65, 66, 67]
>>> image1d.optional_name is None
True

>>> raw_with_name = '\x83ABCsome null terminated name\x00garbage-garbage'
>>> image1d = Image1D.unpack(raw_with_name)

>>> image1d.has_name
1
>>> image1d.numbers
[65, 66, 67]
>>> image1d.optional_name
'some null terminated name'

```

Not only you can use the single value of a field to define the size or the count of other field but you can describe arbitrary  expressions or even use a callable for the more complex one that require statements (which in Python they aren't expressions; think in 'if' statements).

Here is what I mean:

```python
>>> class Matrix(Packet):
...     rows = Int(1)
...     columns = Int(1)
...
...     values = Int(1).repeated(rows * columns) # arithmetic operations

>>> class Address(Packet):
...     ip_address  = Int(1).repeated(4)
...     domain_name = Data(until_marker='\x00').when((ip_address[:3] == [0, 0, 0]) &
...                                                  (ip_address[3]  != 0)) # subscript and comparisions

>>> class Token(Packet):
...     size = Int(1)
...     data = Data(byte_count = lambda pkt, raw, offset, **k: pkt.size if pkt.size < 8 else 8)
...                              # ^-- an arbitrary callable is allowed too


>>> raw_matrix = '\x02\x03ABCDEF'
>>> matrix_2x3 = Matrix.unpack(raw_matrix)

>>> cols = matrix_2x3.columns
>>> matrix_2x3.values[0 : cols]      # first row
[65, 66, 67]
>>> matrix_2x3.values[cols : cols*2] # second row
[68, 69, 70]

>>> raw_resolved_address = '\xc0\xa8\x00\x01'
>>> resolved_address = Address.unpack(raw_resolved_address)

>>> resolved_address.ip_address
[192, 168, 0, 1]
>>> resolved_address.domain_name is None
True

>>> raw_unresolved_address = '\x00\x00\x00\x01example.com\x00'
>>> unresolved_address = Address.unpack(raw_unresolved_address)

>>> unresolved_address.ip_address
[0, 0, 0, 1]
>>> unresolved_address.domain_name
'example.com'

>>> raw_small_token = '\x01A'
>>> small_token = Token.unpack(raw_small_token)

>>> small_token.data
'A'

>>> raw_too_long_token = '\xffABCD1234EFGH5678'
>>> truncated_token = Token.unpack(raw_too_long_token)

>>> truncated_token.data
'ABCD1234'

```
