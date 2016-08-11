In this case we want create simple packet TLP (Type-Length-Payload) with the next format
 - type: 1 byte
 - length: 4 bytes (big endian, unsigned)
 - payload: 'length' bytes

We translate this into a python's class

```python
>>> from packet import Packet
>>> from field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)
```

You can see more about Int and Data in the next session, for now, both Ints are unsigned and
in big endian. The first has only 1 byte. The second has 4 (its default)
The field Data is a little more complicate, its size is not fixed and depend of the value
of the field 'length'

To check that all the fields were correctly created, we can see them

```python
>>> [name for name, field in TLP.get_fields()]
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
''
```

Those values come from the defined defaults of Int (0) and Data ('').
Of course, 'my defaults' may be aren't yours, so you can change them:

```python
>>> p = TLP(type=2) 
>>> p.type
2
>>> p.length
0
>>> p.payload
''
```

This is very convenient but may be it is not the optimal of the default of 'type' is 2
for all the packets that you need. In that case, you can redefine the class and set the
default in the field itself.

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
''
```
