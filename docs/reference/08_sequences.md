# Sequences of Packets

Until now we created a **fixed count** of fields and packets.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Ref

>>> class TypeLenValue(Packet):
...    type = Int(1)
...    length = Int(1)
...    value = Data(length)
```

Now imagine that we need a **list** of them:

```python
>>> class Attributes(Packet):
...    count = Int(1)
...    attributes = Ref(TypeLenValue).repeated(count)
```

`attributes` is a `TypeLenValue` packet **repeated** `count` times.

`bisturi` will represent that as a list as you may expect:

```python
>>> s = b'\x02\x01\x02ab\x04\x03abc'
>>> p = Attributes.unpack(s)    # 2 attributes: '1,2,ab' and '4,3,abc'
>>> p.count
2

>>> for attr in p.attributes:
...     print(attr)
TypeLenValue:
  type: 1
  length: 2
  value: b'ab'
TypeLenValue:
  type: 4
  length: 3
  value: b'abc'

>>> p.pack() == s
True
```

The field is always represented as a list which may contain
zero, one or more elements.

```python
>>> s = b'\x01\x01\x02ab'
>>> p = Attributes.unpack(s)
>>> p.count
1
>>> len(p.attributes)
1
>>> p.attributes[0]
TypeLenValue:
  type: 1
  length: 2
  value: b'ab'

>>> p.pack() == s
True

>>> s = b'\x00'
>>> p = Attributes.unpack(s)
>>> p.count
0
>>> len(p.attributes)
0

>>> p.pack() == s
True
```

## Repeat `until`...

With the `repeated` method we can repeat not only a fixed amount of times
a referenced packet but the count can be dynamic as well.

In the previous example the count was determinate by the `count` field;
in the following example we use a callable.

Imagine that `Attributes` does not have a `count`. Instead the end of
the attributes list is marked by the attribute which `type` is zero.

We can write the following

```python
>>> class Attributes(Packet):
...    attributes = Ref(TypeLenValue).repeated(until=lambda pkt, **k: pkt.attributes[-1].type == 0)
```

The callback receives, among other things, the current packet. Accessing
to `attributes[-1]` gives us the latest attribute unpacked so far.

So `pkt.attributes[-1].type == 0` means unpack the list of `attributes`
**until** the last attribute's `type` is zero.

```python
>>> s =  b'\x01\x02ab\x04\x03abc\x00\x00'
>>> p = Attributes.unpack(s)
>>> for attr in p.attributes:
...     print(attr)
TypeLenValue:
  type: 1
  length: 2
  value: b'ab'
TypeLenValue:
  type: 4
  length: 3
  value: b'abc'
TypeLenValue:
  type: 0
  length: 0
  value: b''

>>> p.pack() == s
True
```

<!--
More cases
>>> s2 = b'\x02\x01a\x00\x00'
>>> q = Attributes.unpack(s2)
>>> len(q.attributes)
2
>>> q.attributes[0].type, q.attributes[0].length, q.attributes[0].value
(2, 1, b'a')
>>> q.attributes[1].type, q.attributes[1].length, q.attributes[1].value
(0, 0, b'')
>>> q.pack() == s2
True

>>> s =  b'\x00\x00'
>>> p = Attributes.unpack(s)    # corner case with 1 single attribute
>>> len(p.attributes)
1
>>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
(0, 0, b'')

>>> p.pack() == s
True
-->

Note how the `attributes` field is created at the *begin* of the parsing and
*updated* later during the parsing.

The `until` callback is then evaluated in each cycle
so you can ask for the last attribute created with `attributes[-1]`.

## Repeat `when`...

By definition then, when you use `until` you have a *one or more*
semantics. (The list will always have at least one element).


To support *zero or more* constructions we need the `when` condition.

Imagine that `Attributes` has a list of attributes like before but also
a flag that says if the list is empty or not.

```python
>>> class Attributes(Packet):
...    has_attributes = Int(1)
...    attributes = Ref(TypeLenValue).repeated(
...                 when=lambda pkt, **k: pkt.has_attributes,
...                 until=lambda pkt, **k: pkt.attributes[-1].type == 0
...                 )
```

The `until` is like the previous example. The new thing is the `when`
condition. This one is evaluated **once before** parsing any attribute.

```python
>>> s = b'\x00'
>>> p = Attributes.unpack(s)
>>> p.has_attributes
0
>>> p.attributes
[]
>>> len(p.attributes)
0

>>> p.pack() == s
True
```
<!--
More tests

>>> s = b'\x01\x01\x02ab\x04\x03abc\x00\x00'
>>> p = Attributes.unpack(s)
>>> len(p.attributes)
3
>>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
(1, 2, b'ab')
>>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
(4, 3, b'abc')
>>> p.attributes[2].type, p.attributes[2].length, p.attributes[2].value
(0, 0, b'')

>>> p.pack() == s
True
-->


The `when` condition can be combined with a fixed count,
but you cannot mix a fixed count with the `until` condition.

```python
>>> class Attributes(Packet):
...    has_attributes = Int(1)
...    attributes = Ref(TypeLenValue).repeated(
...                 count=2,
...                 when=lambda pkt, **k: pkt.has_attributes
...                 )

>>> s = b'\x01\x01\x02ab\x04\x03abc'
>>> p = Attributes.unpack(s)
>>> for attr in p.attributes:
...     print(attr)
TypeLenValue:
  type: 1
  length: 2
  value: b'ab'
TypeLenValue:
  type: 4
  length: 3
  value: b'abc'

>>> p.pack() == s
True

>>> s = b'\x00'
>>> p = Attributes.unpack(s)
>>> p.has_attributes
0
>>> p.attributes
[]

>>> p.pack() == s
True
```

Here is another example with `until`: collect all the attributes
**until** you run out of data to unpack **except** the last 4 bytes.

This is how you would do it:

```python
>>> class Attributes(Packet):
...    attributes = Ref(TypeLenValue).repeated(
...                 until=lambda raw, offset, **k: offset >= (len(raw) - 4)
...                 )
...    checksum = Int(4)

>>> s = b'\x01\x02ab\x04\x03abc\xff\xff\xff\xff'
>>> p = Attributes.unpack(s)
>>> for attr in p.attributes:
...     print(attr)
TypeLenValue:
  type: 1
  length: 2
  value: b'ab'
TypeLenValue:
  type: 4
  length: 3
  value: b'abc'

>>> p.checksum
4294967295

>>> p.pack() == s
True
```

`raw` is the full raw string to be parsed and `offset` is the position
in the string where the parsing is at the moment.

## Optional fields

Final case, what if we want the semantics of *zero or one*? That's it we
want to have a field or subpacket **optional**.

We use the `when` *method*:

```python
>>> class Option(Packet):
...    type = Int(1)
...    num  = Int(4).when(lambda pkt, **k: pkt.type != 0)

>>> s = b'\x01\x00\x00\x00\x04'
>>> p = Option.unpack(s)
>>> p.num
4

>>> p.pack() == s
True

>>> s = b'\x00'
>>> p = Option.unpack(s)
>>> p.num is None
True

>>> p.pack() == s
True
```

