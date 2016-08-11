All the fields accept different ways to define how much they will consume.

This is a summary:

            | Int   | Data | Bits    | Seq count(**) | Seq until  | Seq when  | Ref when
----------- | ----- | ---- | ------- | ------------- | ---------- | --------- | ---------
Fixed       | true  | true | true(*) | true          | no apply   | no apply  | no apply
Other field | false | true | false   | true          | no apply   | no apply  | no apply
Expr field  | false | true | false   | true          | no apply   | true      | true
A callable  | false | true | false   | true          | true       | true      | true


Notes: (\*) The amount set in a Bits fields is the amount of bits, no of bytes, and must be multiple of 8.
      (\*\*) The amount set in a Sequence, is the amount of objects, no of bytes.


First, the simplest one, a fixed amount of bytes (or a fixed amount of bits);
however, there isn't a fixed amount of bytes to be set for referenced objects or sequences:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data, Bits

>>> class AllFixed(Packet):
...    num  = Int(byte_count=1)
...    data = Data(byte_count=1)
...    bits = Bits(bit_count=8)


>>> raw = "\x01\x02\x03"
>>> pkt = AllFixed(raw)
>>> pkt.num, pkt.data, pkt.bits
(1, '\x02', 3)

>>> str(pkt.pack())
'\x01\x02\x03'

```

For sequence of objects you can set the amount of objects to be extracted:

```python
>>> from bisturi.field import Sequence

>>> class FixedSeq(Packet):
...    seq = Int(byte_count=1).repeated(count=3)

>>> raw = "\x01\x02\x03"
>>> pkt = FixedSeq(raw)
>>> pkt.seq
[1, 2, 3]

>>> str(pkt.pack())
'\x01\x02\x03'

```

But fixed amounts it is just the begin. You can define a variable amount using several
methods.
The simplest is using another field, tipically an Int.
Note how you can use this for Data and Sequence fields but not for Int, Bits or Ref fields.

```python
>>> class AllVariable(Packet):
...    amount = Int(byte_count=1)
...    data   = Data(byte_count=amount)
...    seq    = Int(byte_count=1).repeated(count=amount)


>>> raw = "\x01\x01\x02"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('\x01', [2])

>>> str(pkt.pack())
'\x01\x01\x02'

>>> raw = "\x02AA\x01\x02"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('AA', [1, 2])

>>> str(pkt.pack())
'\x02AA\x01\x02'

```

Nice, but it's very common to need to express some amount of bytes in terms of
simple expressions involving one or more fields; not just one field like above.

For example

```python
>>> class AllVariable(Packet):
...    triplet = Int(byte_count=1)
...    data    = Data(byte_count=triplet * 3)
...    seq     = Int(byte_count=1).repeated(count=triplet * 3)


>>> raw = "\x01ABC\x01\x02\x03"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('ABC', [1, 2, 3])

>>> str(pkt.pack())
'\x01ABC\x01\x02\x03'

>>> raw = "\x02ABCDEF\x01\x02\x03\x04\x05\x06"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('ABCDEF', [1, 2, 3, 4, 5, 6])

>>> str(pkt.pack())
'\x02ABCDEF\x01\x02\x03\x04\x05\x06'

```

Don't be shy, lets do more complex expressions

```python
>>> class AllVariable(Packet):
...    rows   = Int(byte_count=1)
...    cols   = Int(byte_count=1)
...    matrix = Int(byte_count=1).repeated(count=rows * cols)


>>> raw = "\x01\x02\x01\x02XXXX"
>>> pkt = AllVariable(raw)
>>> pkt.matrix
[1, 2]

>>> str(pkt.pack())
'\x01\x02\x01\x02'

>>> raw = "\x02\x03\x01\x02\x03\x04\x05\x06"
>>> pkt = AllVariable(raw)
>>> pkt.matrix
[1, 2, 3, 4, 5, 6]

>>> str(pkt.pack())
'\x02\x03\x01\x02\x03\x04\x05\x06'

```

We can go further to use expressions in the until and when conditions:

```python
>>> class AllVariable(Packet):
...    type  = Int(byte_count=1)
...    opt   = Int(byte_count=1).when(type != 0)


>>> raw = "\x01\x02XXX"
>>> pkt = AllVariable(raw)
>>> pkt.opt
2

>>> str(pkt.pack())
'\x01\x02'

>>> raw = "\x00XXX"
>>> pkt = AllVariable(raw)
>>> pkt.opt is None
True

>>> str(pkt.pack())
'\x00'

```

The more flexible method is to use a callable which will be invoked during the
parsing to know how much to consume.
You can use any kind of callable, functions, methods or lambdas.

```python
>>> class VariableUsingCallable(Packet):
...    amount = Int(byte_count=1)
...    data   = Data(byte_count=lambda pkt, **k: pkt.amount * 2)
...    seq    = Int(byte_count=1).repeated(count=lambda pkt, **k: pkt.amount * 2)
...    seq2   = Int(byte_count=1).repeated(until=lambda pkt, **k: pkt.seq2[-1]==0)

>>> raw = "\x01\x00\x01\x02\x03\x00"
>>> pkt = VariableUsingCallable(raw)
>>> pkt.data, pkt.seq, pkt.seq2
('\x00\x01', [2, 3], [0])

>>> str(pkt.pack())
'\x01\x00\x01\x02\x03\x00'

>>> raw = "\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00"
>>> pkt = VariableUsingCallable(raw)
>>> pkt.data, pkt.seq, pkt.seq2
('AABB', [1, 2, 3, 4], [1, 1, 1, 1, 0])

>>> str(pkt.pack())
'\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00'

```

The callable needs to accept a variable keyword-arguments. These are the current
available arguments:
   
   pkt:     the packet, you can use this to access to others fields or methods
   raw:     the full raw data being be parsed.
   offset:  the current offset of the parsed. raw[offset] means the first byte that should be parsed next
   stack:   the stack of packets being be parsed: stack[0] is the higher packet and stack[-1] is the lower (stack[-1] == pkt)

```python
>>> from bisturi.field import Ref

>>> class Lower(Packet):
...    data = Data(byte_count=lambda stack, **k: stack[0].amount)

>>> class Higher(Packet):
...    amount = Int(byte_count=1)
...    lower  = Ref(Lower)

>>> raw = "\x02AA"
>>> pkt = Higher(raw)
>>> pkt.amount, pkt.lower.data
(2, 'AA')

>>> str(pkt.pack())
'\x02AA'

```
