Let's say that we want to calculate the value of a field automatically.

For example we want to calculate the length of a field,
the checksum of the data, or anything like that.

We can do type checking or value checking to a field to ensure that compliances
we some restriction.

To do that, we can replace the value of a field (a simple Python object)
with a *descriptor*.

A descriptor implements the `__get__` and `__set__` methods which are
accessors for the datum behind.

`bisturi` has few descriptors that you can use but you are encouraged
to implement yours.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int
>>> from bisturi.descriptor import AutoLength

>>> class DataExample(Packet):
...    length = Int(1).describe(AutoLength("a"))
...    a = Data(length)
...
```

The field length will be access through the `AutoLength` descriptor.

In this case, the `__get__` method will return the length of the field trackd,
`a` in this case.

```python
>>> s = b'\x02ab'
>>> p = DataExample.unpack(s)
>>> p.length
2
>>> p.a
b'ab'

>>> p.a = b"abc"     # change only this field
>>> p.length        # and this other gets updated automatically
3
>>> p.a
b'abc'

>>> hasattr(p, '__dict__') # double check that we didn't introduce an extra dict
False

>>> p.pack()
b'\x03abc'
```

To ensure that we are talking with a descriptor, we can do the following test:

```python
>>> isinstance(DataExample.length, AutoLength)
True
```

Setting an explicit value disabled `AutoLength`:

```python
>>> q = DataExample(length=3, a=b'ab')
>>> q.length    # forced by us
3
>>> q.a
b'ab'
```

You can re-enable *deleting* the value set before:

```python
>>> del q.length
>>> q.length
2
>>> q.a
b'ab'
```

`bisturi` offers also a more general descriptor, `Auto`, which
allows to execute an arbitrary function instead of calculate
the length of some other field.

For example if we need to compute the length in bits of some data, we can do:

```python
>>> from bisturi.descriptor import Auto

>>> class DataExample(Packet):
...    length_in_bits = Int(1).describe(Auto(lambda pkt: len(pkt.a) * 8))
...    a = Data(length_in_bits // 8)
...
```

And this descriptor will works in the same way that `AutoLength`:

```python
>>> s = b'\x10ab'
>>> p = DataExample.unpack(s)
>>> p.length_in_bits
16
>>> p.a
b'ab'

>>> p.a = b"abc"
>>> p.length_in_bits
24
>>> p.a
b'abc'
```

