Until now we created a fixed count of fields and packets. But if we need a list of them?
Take this simple packet

>>> from packet import Packet
>>> from field  import Data, Int, Ref

>>> class TypeLenValue(Packet):
...    type = Int(1)
...    length = Int(1)
...    value = Data(length)

Now imagine that we need a list of them

>>> class Attributes(Packet):
...    count = Int(1)
...    attributes = Ref(TypeLenValue).repeated(count)

So,

>>> s = '\x02\x01\x02ab\x04\x03abc'
>>> p = Attributes(s)
>>> p.count
2
>>> len(p.attributes)
2
>>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
(1, 2, 'ab')
>>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
(4, 3, 'abc')

>>> p.to_raw() == s
True

With the 'repeated' method we can repeat a fixed amount of times.
But the method can do more and in a more dynamic way:

>>> class Attributes(Packet):
...    attributes = Ref(TypeLenValue).repeated(until=lambda p: p.attributes[-1].type == 0)

>>> s = '\x01\x02ab\x04\x03abc\x00\x00'
>>> p = Attributes(s)
>>> len(p.attributes)
3
>>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
(1, 2, 'ab')
>>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
(4, 3, 'abc')
>>> p.attributes[2].type, p.attributes[2].length, p.attributes[2].value
(0, 0, '')

>>> p.to_raw() == s
True

The 'until' keyword assume that the subpacket TypeLenValue was extracted and put in
the attributes list being enabled to be inspected by the 'until' callback.
It's clear that this works like 'one-or-more' construction.


>>> class Attributes(Packet):
...    attributes = Ref(TypeLenValue).repeated(until=lambda p, stream: not stream.is_end())
