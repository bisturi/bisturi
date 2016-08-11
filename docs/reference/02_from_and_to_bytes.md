Now it's time to see how we can create packets from a string and how we can see a packet 
as a string of bytes

First, we create a simple packet class

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)

```

Now, let be the next string of bytes (try to see the values encoded in it)

```python
>>> s1 = '\x02\x00\x00\x00\x03abc'

```

You can see what should be the value of 'type' or 'payload'? 
I hope!. If not, let the packet dissect the string for you

```python
>>> p = TLP(s1)
>>> p.type
2
>>> p.length
3
>>> p.payload
'abc'

```

And another example

```python
>>> s2 = '\x01\x00\x00\x00\x01d'
>>> q = TLP(s2)
>>> q.type
1
>>> q.length
1
>>> q.payload
'd'

```

You can see that 'type' and the other fields are class attributes. However the value
of each field is keep per instance, so:

```python
>>> p.type
2
>>> q.type
1

```

are different, which make sense.

Now, from the packet to the string

```python
>>> p.pack() == s1
True
>>> q.pack() == s2
True

```

Finally, you can set the offset of the string where to start to read. By default is 0.
However, to use this you need to call unpack directly.

```python
>>> s2 = 'xxx\x01\x00\x00\x00\x01d'
>>> q = TLP()
>>> q.unpack(s2, 3) #ignore the first 3 bytes "xxx"
9
>>> q.type
1
>>> q.length
1
>>> q.payload
'd'

```

If a field cannot be unpacked, an exception is raised with the full stack of packets and offsets:

```python
>>> class VariablePayload(Packet):
...    length = Int(1)
...    payload = Data(length)

>>> def some_function(raw):
...    q = VariablePayload()
...    q.unpack(raw)

>>> s = '\x04a'
>>> some_function(s)                                         #doctest: +ELLIPSIS
Traceback (most recent call last):
...
PacketError: Error when unpacking the field 'payload' of packet VariablePayload at 00000001: Unpacked 1 bytes but expected 4
Packet stack details: 
    00000001 VariablePayload                .payload
Field's exception:
...
Exception: Unpacked 1 bytes but expected 4...

```

The same is true if the packet cannot be packed into a string:

```python
>>> p = VariablePayload()
>>> p.length = "invalid"

>>> p.pack()                                    #doctest: +ELLIPSIS
Traceback (most recent call last):
...
PacketError: Error when packing the field 'length' of packet VariablePayload at 00000000: cannot convert argument to integer
Packet stack details: 
    00000000 VariablePayload                .length
Field's exception:
...

```
