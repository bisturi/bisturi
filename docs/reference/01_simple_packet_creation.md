In this case we want to create a simple packet TLP (Type-Length-Payload) with the next format
 - type: 1 byte
 - length: 4 bytes (big endian, unsigned)
 - payload: 'length' bytes

We translate this into a python's class

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)

```

One of the primary goals of bisturi is to be simple and easy to read. In the best cases
reading a packet class is almost the same as reading the specification of the format, protocol
or RFC.

You can see more about Int and Data in the next sections, but for now we will keep the things
simple: both Ints are unsigned and in big endian which it is the default in bisturi. 

The first Int has only 1 byte. The second has 4 (its default).

The field Data is a little more interesting because its size is not fixed and depends of the value
of the field 'length'.

To check that all the fields were correctly created, we can see them

```python
>>> [name for name, field, _, _ in TLP.get_fields()]
['type', 'length', 'payload']

```

Ok, now lets intantiate a TLP packet and see its values by default

```python
>>> p = TLP()
>>> p.type
0
>>> p.length
0
>>> p.payload
b''

```

Those values come from the defined defaults of Int and Data which are 0 and '' respectively.
Of course, 'my defaults' may be aren't yours, so you can change them per packet instance:

```python
>>> p = TLP(type=2)
>>> p.type
2
>>> p.length
0
>>> p.payload
b''

```

or change the default for all the packet's instances redefining the class and setting the 
default in the field itself:

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

