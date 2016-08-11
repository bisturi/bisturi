Until now we created a fixed count of fields and packets. But if we need a list of them?
Take this simple packet

::

   >>> from packet import Packet
   >>> from field  import Data, Int, Ref

   >>> class TypeLenValue(Packet):
   ...    type = Int(1)
   ...    length = Int(1)
   ...    value = Data(length)

Now imagine that we need a list of them

::

   >>> class Attributes(Packet):
   ...    count = Int(1)
   ...    attributes = Ref(TypeLenValue).repeated(count)

So,

::

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

   >>> p.pack() == s
   True

The field is always represented as a list. One and Zero counts are valid too.

::
   
   >>> s = '\x01\x01\x02ab'
   >>> p = Attributes(s)
   >>> p.count
   1
   >>> len(p.attributes)
   1
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (1, 2, 'ab')

   >>> p.pack() == s
   True

::
   
   >>> s = '\x00'
   >>> p = Attributes(s)
   >>> p.count
   0
   >>> len(p.attributes)
   0

   >>> p.pack() == s
   True

With the 'repeated' method we can repeat a fixed amount of times.
But the method can do more and in a more dynamic way:

For example, the field 'attributes' can be a list that ends with a special
'Attribute' type (zero in this example):

::

   >>> class Attributes(Packet):
   ...    attributes = Ref(TypeLenValue).repeated(until=lambda p, *args: p.attributes[-1].type == 0)

   >>> s =  '\x01\x02ab\x04\x03abc\x00\x00'
   >>> s2 = '\x02\x01a\x00\x00'
   >>> p = Attributes(s)
   >>> q = Attributes(s2)
   >>> len(p.attributes)
   3
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (1, 2, 'ab')
   >>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
   (4, 3, 'abc')
   >>> p.attributes[2].type, p.attributes[2].length, p.attributes[2].value
   (0, 0, '')

   >>> len(q.attributes)
   2
   >>> q.attributes[0].type, q.attributes[0].length, q.attributes[0].value
   (2, 1, 'a')
   >>> q.attributes[1].type, q.attributes[1].length, q.attributes[1].value
   (0, 0, '')

   >>> p.pack() == s
   True
   >>> q.pack() == s2
   True

::

   >>> s =  '\x00\x00'
   >>> p = Attributes(s)
   >>> len(p.attributes)
   1
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (0, 0, '')

   >>> p.pack() == s
   True

Note how the 'attributes' field is created at the begin of the parsing and 
updated during the parsing. The 'until' callback is then evaluated in each cycle
so you can ask for the last attribute created with 'attributes[-1]'.

The 'until' keyword assume that the subpacket TypeLenValue was extracted and put in
the attributes list being enabled to be inspected by the 'until' callback.
It's clear that this works like 'one-or-more' construction.

To support 'zero-or-more' constructions we need the 'when' condition:

::

   >>> class Attributes(Packet):
   ...    has_attributes = Int(1)
   ...    attributes = Ref(TypeLenValue).repeated(when=lambda p, *args: p.has_attributes, until=lambda p, *args: p.attributes[-1].type == 0)

   >>> s = '\x01\x01\x02ab\x04\x03abc\x00\x00'
   >>> p = Attributes(s)
   >>> len(p.attributes)
   3
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (1, 2, 'ab')
   >>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
   (4, 3, 'abc')
   >>> p.attributes[2].type, p.attributes[2].length, p.attributes[2].value
   (0, 0, '')

   >>> p.pack() == s
   True

   >>> s = '\x00'
   >>> p = Attributes(s)
   >>> p.has_attributes
   0
   >>> p.attributes
   []
   >>> len(p.attributes)
   0

   >>> p.pack() == s
   True

The 'when' condition can be combinated with a fixed count, like:

::

   >>> class Attributes(Packet):
   ...    has_attributes = Int(1)
   ...    attributes = Ref(TypeLenValue).repeated(2, when=lambda p, *args: p.has_attributes)

   >>> s = '\x01\x01\x02ab\x04\x03abc'
   >>> p = Attributes(s)
   >>> len(p.attributes)
   2
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (1, 2, 'ab')
   >>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
   (4, 3, 'abc')

   >>> p.pack() == s
   True

   >>> s = '\x00'
   >>> p = Attributes(s)
   >>> p.has_attributes
   0
   >>> p.attributes
   []
   >>> len(p.attributes)
   0

   >>> p.pack() == s
   True

But you cannot mix a fixed count with the 'until' condition.


We can use even more complicated conditions like 'consume' all the data until the end
of the stream but leaving 4 byte at the end.

::

   >>> class Attributes(Packet):
   ...    attributes = Ref(TypeLenValue).repeated(until=lambda p, raw, offset: offset >= (len(raw) - 4))
   ...    checksum = Int(4)
   
   >>> s = '\x01\x02ab\x04\x03abc\xff\xff\xff\xff'
   >>> p = Attributes(s)
   >>> len(p.attributes)
   2
   >>> p.attributes[0].type, p.attributes[0].length, p.attributes[0].value
   (1, 2, 'ab')
   >>> p.attributes[1].type, p.attributes[1].length, p.attributes[1].value
   (4, 3, 'abc')

   >>> p.pack() == s
   True

Here, 'raw' is the full raw string to be parsed and 'offset' is the position in the string
where the parsing is taking effect.
