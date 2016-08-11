All the fields accept different ways to define how much they will consume.

This is a summary:

            | Int   | Data | Bits    | Seq count(**) | Seq until  | Seq when
----------- | ----- | ---- | ------- | ------------- | ---------- | ---------
Fixed       | true  | true | true(*) | true          | no apply   | no apply
Other field | false | true | false   | true          | no apply   | no apply
A callable  | false | true | false   | true          | true       | true


Notes: (\*) The amount set in a Bits fields is the amount of bits, no of bytes, and must be multiple of 8.
      (\*\*) The amount set in a Sequence, is the amount of objects, no of bytes.


First, the simplest one, a fixed amount of bytes (or a fixed amount of bits);
however, there isn't a fixed amount of bytes to be set for referenced objects or sequences:

```python
>>> from packet import Packet
>>> from field import Int, Data, Bits

>>> class AllFixed(Packet):
...    num  = Int(byte_count=1)
...    data = Data(byte_count=1)
...    bits = Bits(bit_count=8)


>>> raw = "\x01\x02\x03"
>>> pkt = AllFixed(raw)
>>> pkt.num, pkt.data, pkt.bits
(1, '\x02', 3)

>>> pkt.pack()
'\x01\x02\x03'

```

For sequence of objects you can set the amount of objects to be extracted:

```python
>>> from field import Sequence

>>> class FixedSeq(Packet):
...    seq = Int(byte_count=1).repeated(count=3)

>>> raw = "\x01\x02\x03"
>>> pkt = FixedSeq(raw)
>>> pkt.seq
[1, 2, 3]

>>> pkt.pack()
'\x01\x02\x03'

```

But fixed amounts it is just the begin. You can define a variable amount using several
methods.
The simplest is using another field, tipically an Int.
Note how you can use this for Data an Sequence fields but not for Int, Bits or Ref fields.

```python
>>> class AllVariable(Packet):
...    amount = Int(byte_count=1)
...    data   = Data(byte_count=amount)
...    seq    = Int(byte_count=1).repeated(count=amount)


>>> raw = "\x01\x01\x02"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('\x01', [2])

>>> pkt.pack()
'\x01\x01\x02'

>>> raw = "\x02AA\x01\x02"
>>> pkt = AllVariable(raw)
>>> pkt.data, pkt.seq
('AA', [1, 2])

>>> pkt.pack()
'\x02AA\x01\x02'

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

>>> pkt.pack()
'\x01\x00\x01\x02\x03\x00'

>>> raw = "\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00"
>>> pkt = VariableUsingCallable(raw)
>>> pkt.data, pkt.seq, pkt.seq2
('AABB', [1, 2, 3, 4], [1, 1, 1, 1, 0])

>>> pkt.pack()
'\x02AABB\x01\x02\x03\x04\x01\x01\x01\x01\x00'

```

The callable needs to accept a variable keyword-arguments. These are the current
available arguments:
   
   pkt:     the packet, you can use this to access to others fields or methods
   raw:     the full raw data being be parsed.
   offset:  the current offset of the parsed. raw[offset] means the first byte that should be parsed next
   stack:   the stack of packets being be parsed: stack[0] is the higher packet and stack[-1] is the lower (stack[-1] == pkt)

```python
>>> from field import Ref

>>> class Lower(Packet):
...    data = Data(byte_count=lambda stack, **k: stack[0].amount)

>>> class Higher(Packet):
...    amount = Int(byte_count=1)
...    lower  = Ref(Lower)

>>> raw = "\x02AA"
>>> pkt = Higher(raw)
>>> pkt.amount, pkt.lower.data
(2, 'AA')

>>> pkt.pack()
'\x02AA'

```
