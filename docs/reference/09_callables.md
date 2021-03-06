# Callables

All the fields accept different ways to define how much they will consume.

This is a summary:

```
                                     |          Sequence's            |   Ref's
            | Int   | Data | Bits    | count(2) |  until   |   when   |   when
----------- | ----- | ---- | ------- | -------- | -------- | -------- | ---------
Fixed       | true  | true | true(1) | true     | no apply | no apply | no apply
Other field | false | true | false   | true     | no apply | no apply | no apply
Expr field  | false | true | false   | true     | no apply | true     | true
A callable  | false | true | false   | true     | true     | true     | true
```

Notes:
 - (1) The amount set in a Bits fields is the amount of bits, no of bytes.
 - (2) The amount set in a Sequence, is the amount of objects, no of bytes.


## Fixed count

First, the simplest one, a fixed amount of bytes (or a fixed amount of bits);

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data, Bits

>>> class AllFixed(Packet):
...    num  = Int(byte_count=1)
...    data = Data(byte_count=1)
...    bits = Bits(bit_count=8)


>>> raw = b"\x01\x02\x03"
>>> pkt = AllFixed.unpack(raw)
>>> pkt.num, pkt.data, pkt.bits
(1, b'\x02', 3)

>>> pkt.pack()
b'\x01\x02\x03'
```

For sequence of objects you set the amount of objects to be extracted,
not the count of bytes:

```python
>>> class FixedSeq(Packet):
...    seq = Int(byte_count=1).repeated(count=3)

>>> raw = b"\x01\x02\x03"
>>> pkt = FixedSeq.unpack(raw)
>>> pkt.seq
[1, 2, 3]

>>> pkt.pack()
b'\x01\x02\x03'
```

## Field and field expressions

A variable amount of bytes can be done using another field, typically an
`Int`.

Note how you can use this for `Data` and `Sequence` fields
but not for `Int`, `Bits` or `Ref` fields (at least for now).

```python
>>> class AllVariable(Packet):
...    amount = Int(byte_count=1)
...    data   = Data(byte_count=amount)
...    seq    = Int(byte_count=1).repeated(count=amount)


>>> raw = b"\x01\x01\x02"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.data, pkt.seq
(b'\x01', [2])

>>> pkt.pack()
b'\x01\x01\x02'

>>> raw = b"\x02AA\x01\x02"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.data, pkt.seq
(b'AA', [1, 2])

>>> pkt.pack()
b'\x02AA\x01\x02'
```

Nice, but a field is just a particular case of something more general:
*field expressions*.

For example:

```python
>>> class AllVariable(Packet):
...    triplet = Int(byte_count=1)
...    data    = Data(byte_count=triplet * 3)   # multiplication by a constant
...    seq     = Int(byte_count=1).repeated(count=triplet * 3)


>>> raw = b"\x01ABC\x01\x02\x03"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.data, pkt.seq
(b'ABC', [1, 2, 3])

>>> pkt.pack()
b'\x01ABC\x01\x02\x03'

>>> raw = b"\x02ABCDEF\x01\x02\x03\x04\x05\x06"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.data, pkt.seq
(b'ABCDEF', [1, 2, 3, 4, 5, 6])

>>> pkt.pack()
b'\x02ABCDEF\x01\x02\x03\x04\x05\x06'
```

Don't be shy, lets do more complex expressions combining multiple fields
in a single field expression:

```python
>>> class AllVariable(Packet):
...    rows   = Int(byte_count=1)
...    cols   = Int(byte_count=1)
...    matrix = Int(byte_count=1).repeated(count=rows * cols)


>>> raw = b"\x01\x02\x01\x02XXXX"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.matrix
[1, 2]

>>> pkt.pack()
b'\x01\x02\x01\x02'

>>> raw = b"\x02\x03\x01\x02\x03\x04\x05\x06"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.matrix
[1, 2, 3, 4, 5, 6]

>>> pkt.pack()
b'\x02\x03\x01\x02\x03\x04\x05\x06'
```

Here are more:

 - comparison
 - byte substring
 - logical operators (`&` for `and` and `|` for `or`)

```python
>>> class Magic(Packet):
...    magic = Data(4, default=b'v002')
...    v2_only_field = Data(2).when(magic == b'v002')
...    hidden_field  = Data(4).when((magic[:3] == b'xyz') & (magic[3] != b'\x00'))


>>> raw = b"v002AB"
>>> pkt = Magic.unpack(raw)
>>> pkt.v2_only_field
b'AB'
>>> pkt.hidden_field is None
True

>>> pkt.pack()
b'v002AB'

>>> raw = b"xyz1beef"
>>> pkt = Magic.unpack(raw)
>>> pkt.v2_only_field is None
True
>>> pkt.hidden_field
b'beef'

>>> pkt.pack()
b'xyz1beef'
```

We can go further to use expressions in the `until` and `when` conditions:

```python
>>> class AllVariable(Packet):
...    type  = Int(byte_count=1)
...    opt   = Int(byte_count=1).when(type != 0)


>>> raw = b"\x01\x02XXX"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.opt
2

>>> pkt.pack()
b'\x01\x02'

>>> raw = b"\x00XXX"
>>> pkt = AllVariable.unpack(raw)
>>> pkt.opt is None
True

>>> pkt.pack()
b'\x00'
```

## Callable

The more flexible method is to use a callable which will be invoked during the
parsing to know how much to consume.

You can use any kind of callable: functions, methods and lambdas.

```python
>>> class VariableUsingCallable(Packet):
...    amount = Int(byte_count=1)
...    data   = Data(byte_count=lambda pkt, **k: pkt.amount * 2)
...    seq    = Int(byte_count=1).repeated(count=lambda pkt, **k: pkt.amount * 2)
...    seq2   = Int(byte_count=1).repeated(until=lambda pkt, **k: pkt.seq2[-1]==0)

>>> raw = b"\x01\x00\x01\x02\x03\x00"
>>> pkt = VariableUsingCallable.unpack(raw)
>>> pkt.data, pkt.seq, pkt.seq2
(b'\x00\x01', [2, 3], [0])

>>> pkt.pack()
b'\x01\x00\x01\x02\x03\x00'

>>> raw = b"\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00"
>>> pkt = VariableUsingCallable.unpack(raw)
>>> pkt.data, pkt.seq, pkt.seq2
(b'AABB', [1, 2, 3, 4], [1, 1, 1, 1, 0])

>>> pkt.pack()
b'\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00'

```

The callable will receive the following keyword-arguments:

 - `pkt`: the packet, you can use this to access to other fields or methods.
 - `raw`: the full raw data being be parsed.
 - `offset`: the current offset of the parsed: `raw[offset]` means
the first byte that should be parsed next.
 - `root`: the packet which started the `unpack`/`pack` operation; it
may not be `pkt`.

```python
>>> from bisturi.field import Ref

>>> class Lower(Packet):
...    data = Data(byte_count=lambda root, **k: root.amount)

>>> class Higher(Packet):
...    amount = Int(byte_count=1)
...    lower  = Ref(Lower)

>>> raw = b"\x02AA"
>>> pkt = Higher.unpack(raw)
>>> pkt.amount, pkt.lower.data
(2, b'AA')

>>> pkt.pack()
b'\x02AA'
```


