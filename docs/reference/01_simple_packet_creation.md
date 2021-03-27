We will begin with a simple packet called Type-Length-Payload or TLP.

It consists of three fields:
 - `type`: 1 byte
 - `length`: 4 bytes (big endian, unsigned)
 - `payload`: `length` bytes

We translate this into a Python's class

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)
```

One of the primary goals of `bisturi` is to be **simple and easy to read**.

In the best cases reading a packet class is almost the same as reading
the specification of the format, protocol or RFC.


We will explore more about Int and Data in the following sections, but for now
a few notes:
 - `Int(1)` denotes an *integer* field, a number of 1 byte length,
unsigned and in big endian.
 - `Int(4)` denotes also an unsigned, big endian number but this time is
of 4 bytes.
 - `Data(length)` denotes arbitrary data and its length is not fixed but
variable and it depends of the value of the field `length`.

Ok, now let's instantiate a `TLP` packet:

```python
>>> p = TLP()
>>> p.type
0
>>> p.length
0
>>> p.payload
b''
```

Those values come from the defined defaults for `Int` and `Data`
which are `0` and `''` respectively.

Of course, *my defaults* may not be yours, so you can change
them per packet instance:

```python
>>> p = TLP(type=2)
>>> p.type
2
>>> p.length
0
>>> p.payload
b''
```

Or you can change the default in its definition so all the instances
will inherit it:

```python
>>> class TLP(Packet):
...    type = Int(1, default=2)
...    length = Int()
...    payload = Data(length)

>>> p = TLP()
>>> p.type
2
>>> p.length
0
>>> p.payload
b''
```

One last comment, `get_fields` is a special class method to
retrieve, among other things, the name of the fields.

```python
>>> [name for name, _, _, _ in TLP.get_fields()]
['type', 'length', 'payload']
```

So, we have an idea of how to create packet definitions. What we can do
with them?
