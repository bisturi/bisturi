Let's say that we want to calculate the value of a field automatically. 
For example we want to calculate the length of a field, the checksum of the data,
or anything like that.
We can do type checking or value checking to a field to ensure that compliances
we some restriction.

To do that, we can replace the value of a field (a simple python object) by a descriptor.
A descriptor implements the __get__ and __set__ methods which are accessors for the datum
behind.

The lib has few descriptors that you can use but you are encouraged to implement the yours.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Bkpt
>>> from bisturi.descriptor import AutoLength

>>> class DataExample(Packet):
...    length = Int(1).describe(AutoLength("a"))
...    a = Data(length)
...

```

The field length will be access through the AutoLength descriptor. In this case, the 
__get__ method will return the length of the field tracked ("a" in this case)

```python
>>> s = b'\x02ab'
>>> p = DataExample.unpack(s)
>>> p.length
2
>>> p.a
'ab'

>>> p.a = b"abc"     # change only this field
>>> p.length        # and this other gets updated automatically
3
>>> p.a
'abc'

```

To ensure that we are talking with a descriptor, we can do the following test:

```python
>>> isinstance(DataExample.length, AutoLength)
True

```

Notice how the real value still has the original value of 2. This is fine until we need
to pack. The real value will be used instead of the computed one.
In some how, we need to synchronize both attributes. 

For that purpose, the descriptor can implement the methods sync_before_pack and sync_after_unpack.
The AutoLength descriptor implement sync_before_pack so th pack method works as expected:

```python
>>> p.pack()
'\x03abc'

```

AutoLength support to force a value disabling the auto-functionality

```python
>>> q = DataExample(length=3, a=b'ab')
>>> q.length
3
>>> q.a
'ab'

```

You can reenable 'deleting' the value set before:

```python
>>> del q.length
>>> q.length
2
>>> q.a
'ab'

```

There is a more general descriptor available that allows to execute an arbitrary function instead of calculate
the length of some other field.
For example if we need to compute the length in bits of some data, we can do:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Bkpt
>>> from bisturi.descriptor import Auto

>>> class DataExample(Packet):
...    length_in_bits = Int(1).describe(Auto(lambda pkt: len(pkt.a) * 8))
...    a = Data(length_in_bits // 8)
...

```

An this descriptor will works in the same way that AutoLength:

```python
>>> s = b'\x10ab'
>>> p = DataExample.unpack(s)
>>> p.length_in_bits
16
>>> p.a
'ab'

>>> p.a = b"abc"
>>> p.length_in_bits
24
>>> p.a
'abc'

```

