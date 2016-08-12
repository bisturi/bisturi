In this example will create the Ethernet Packet.
Using Data and Int it's a relative simple task.

```python
>>> from bisturi.field import Data, Int
>>> from bisturi.packet import Packet

>>> class Ethernet(Packet):
...    destination = Data(6)
...    source = Data(6)
...    size = Int(2)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)

```

The problem with this is that the fields 'destination' and 'source' are not randoms bytes.
In fact they are the MAC of the statations.
It should be nice to create a packet for MAC and utilize it in Ethernet. For that we can use
the Ref field in the Ethernet packet to reference another packet, the MAC packet:

```python
>>> from bisturi.field import Ref
>>> class MAC(Packet):
...    oui = Data(3)
...    nic = Data(3)

>>> class Ethernet(Packet):
...    destination = Ref(MAC)
...    source = Ref(MAC)
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)

```

So, we can do this

```python
>>> s1 = '\x00\x01\x01\x00\x00\x01\x00\x01\x01\x00\x00\x02\x05hello'
>>> s2 = '\x00\x01\x01\x00\x00\x02\x00\x01\x01\x00\x00\x01\x05world'
>>>
>>> p = Ethernet.unpack(s1)
>>> q = Ethernet.unpack(s2)
>>>
>>> p.destination.nic
'\x00\x00\x01'
>>> p.source.nic
'\x00\x00\x02'
>>> p.size
5
>>> p.payload
'hello'
>>>
>>> q.destination.nic
'\x00\x00\x02'
>>> q.source.nic
'\x00\x00\x01'
>>> q.size
5
>>> q.payload
'world'

>>> p.pack() == s1
True
>>> q.pack() == s2
True

```

The Ref field accept a Packet subclass or a Field subclass, but if you need 
to set defaults parameters to the referenced object, you need to pass it instead.
(In other words Ref(MAC) is the same that Ref(MAC()), the first is just a shortcut)

```python
>>> class Ethernet(Packet):
...    destination = Ref(MAC(nic='\xff\xff\x01'))
...    source = Ref(MAC(nic='\xff\xff\x02'))
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)

>>> p = Ethernet()
>>>
>>> p.destination.nic
'\xff\xff\x01'
>>> p.source.nic
'\xff\xff\x02'

```


The use of Ref is most like a shortcut instead of create a new class which extends Field
but at the cost of another level of indirection.
You can see how to create your custom fields but this require a little more of knowlage
about the lib.

The Ref should not be used to link layers or compose unrelated packets. For example, if you have
the packet Ethernet and the packet IP, maybe you will be temted to define 
Ethernet.payload as Ref(IP) but this will bound your Ethernet implementation to IP.

It is possible to use a subpacket (a packet defined inside of another) as a shortcut instead of using
Ref. This is an example:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class Person(Packet):
...    length = Int(1)
...    name = Data(length)
...
...    class BirthDate(Packet):
...        day   = Int(1)
...        month = Int(1)
...        year  = Int(2)
...
...    age = Int(1)
...

>>> s = "\x04john\x05\x03\x07\xda\x16"
>>> p = Person.unpack(s)

>>> p.length
4
>>> p.name
'john'
>>> p.age
22
>>> p.birth_date.day
5
>>> p.birth_date.year
2010

```

Notice how the packet' name "BirthDate" is transformed into the "birth_date" field. 
The rules follow the pyhonic path for names, transforming class's names like "FooBar" into field's names like "foo_bar".

We can do a last improvement. Some times we use sub packets to organize better the
structure of the big picture but it become annoying the extra level of indirection.
To makes this more easy to use we can 'embeb' the fields of the referenced sub packet
into the packet container:

```python
>>> class Frame(Packet):
...    address = Ref(Ethernet, embeb=True)

>>> p = Frame()
>>>
>>> p.destination.nic  # direct access, no p.address.destination
'\xff\xff\x01'
>>> p.source.nic
'\xff\xff\x02'

```

