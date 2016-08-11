Now it's time to see how we can create packets from a string and how we can see a packet 
as a string of bytes

First, we create a simple packet class

>>> from packet import Packet
>>> from field import Int, Data
>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)

Now, let be the next string of bytes (try to see the values encoded in it)

>>> s1 = '\x02\x00\x00\x00\x03abc'

You can see what should be the value of 'type' or 'payload'? 
I hope!. If not, let the packet dissect the string for you

>>> p = TLP(s1)
>>> p.type
2
>>> p.length
3
>>> p.payload
'abc'

And another example
>>> s2 = '\x01\x00\x00\x00\x01d'
>>> q = TLP(s2)
>>> q.type
1
>>> q.length
1
>>> q.payload
'd'

You can see that 'type' and the other fields are class attributes. However the value
of each field is keep per instance, so:

>>> p.type
2
>>> q.type
1

are different, which make sense.

Now, from the packet to the string

>>> p.to_raw() == s1
True
>>> q.to_raw() == s2
True

