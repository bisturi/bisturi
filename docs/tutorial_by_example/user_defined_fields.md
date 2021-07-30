# User Defined Fields

A lot of packets and structures can be built using the primitive
*fields* of `bisturi`: `Int`, `Data` and `Bits`.

But what if we want something custom? Consider a packet that
has two attributes that represent two MAC addresses.

Using only the primitive fields we would have to write something like
this:

```python
>>> from bisturi import Packet, Data

>>> class Message(Packet):
...    sender_addr = Data(6)
...    receiver_addr = Data(6)
```

Yes, a MAC address is a binary blob of 6 bytes, but working with bytes
is **awkward**. A MAC is a much richer object like the one made with
[netaddr](https://pythonhosted.org/netaddr/api.html)

Considere the following MAC address:

```python
>>> from netaddr import EUI         # byexample: +fail-fast

>>> addr = EUI("00:1b:77:49:54:fd")
>>> addr.oui.registration()         # byexample: +timeout=8
{'address': ['Lot 8, Jalan Hi-Tech 2/3', 'Kulim  Kedah  09000', 'MY'],
 'idx': 7031,
 'offset': 277367,
 'org': 'Intel Corporate',
 'oui': '00-1B-77',
 'size': 139}
```

It would be much convenient to define `Message` as:

```python
>>> class Message(Packet):                                  # byexample: +skip
...     sender_addr = MAC()
...     receiver_addr = MAC()

>>> pkt = Message(sender_addr="00:1b:77:49:54:fd")          # byexample: +skip
>>> pkt.sender_addr.oui.registration()                      # byexample: +skip
{'address': ['Lot 8, Jalan Hi-Tech 2/3', 'Kulim  Kedah  09000', 'MY'],
 'idx': 7031,
 'offset': 277367,
 'org': 'Intel Corporate',
 'oui': '00-1B-77',
 'size': 139}
```

In `bisturi` a *field* is a Python class that **maps** a Python object
to bytes and viceversa.

It is then quite simple to create *user defined fields*:

```python
>>> from bisturi import Field

>>> class MAC(Field):
...     def __init__(self, default=EUI(0)):
...         super().__init__()
...         self.default = default
...
...     def init(self, packet, defaults):
...         obj = defaults.get(self.field_name, self.default)
...         setattr(packet, self.field_name, obj)
...
...     def pack(self, pkt, fragments, **k):
...         obj = getattr(pkt, self.field_name)
...         fragments.append(obj.packed)
...         return fragments
...
...     def unpack(self, pkt, raw, offset=0, **k):
...         obj = EUI(raw[offset:offset+6].hex())
...         setattr(pkt, self.field_name, obj)
...
...         return offset+6
```

Let's digest that piece by piece:

 - `__init__` receives a default Python object and calls `Field`
constructor. The default is stored in the field instance as any other
attribute.
 - `init` gets the default Python object and *stores* it into the packet
object. There are two possible defaults: the one set during the packet
creation and the other set in `__init__`.
 - `pack` *gets* the Python object from the packet and somehow
*serializes* it. In this case we use `EUI.packed` to get a byte
representation of the MAC and we store this into `fragments`, a container
for chunks of bytes provided by `bisturi`.
 - `unpack` does the opposite, it *de-serializes* 6 bytes into a Python
object. The method receives the **whole** `raw` byte string and the
*offset* where the field should grab its bytes. Once obtained the Python
object (`EUI`) *stores* it into the packet and return the updated
offset.

For storing and retrieving the Python object from the packet are used
`setattr` and `getattr` with `self.field_name` as the name of the slot
to save/read the object. It is defined by `bisturi` so you don't have to
worry.

Here is how `Message` looks now:

```python
>>> class Message(Packet):
...     sender_addr = MAC()
...     receiver_addr = MAC(default=EUI('00:50:c2:00:0f:01'))

>>> pkt = Message(sender_addr=EUI("00:1b:77:49:54:fd"))
>>> pkt.sender_addr
EUI('00-1B-77-49-54-FD')
>>> pkt.receiver_addr
EUI('00-50-C2-00-0F-01')

>>> Message.unpack(pkt.pack())
Message:
  sender_addr: 00-1B-77-49-54-FD
  receiver_addr: 00-50-C2-00-0F-01
```

Note the values:

 - `sender_addr` was set in the `Message` construction and *overrides*
the default of `MAC` (see `init` method).
 - `receiver_addr` was not set any value in `Message` so the field's
default is used (again, see `init` method).

That's all what it takes to create a field but we can go a little
further.

`bisturi` does not enforce any type checking when setting a field
so the following is valid:

```python
>>> pkt.sender_addr = "foo"
```

Of course, it is *"valid"* until we try to pack it:

```python
>>> pkt.pack()              # byexample: +norm-ws
<...>.PacketError: Error when packing the field 'sender_addr'
of packet Message at 00000000: 'str' object has no attribute 'packed'
<...>
```

Let's fix this.

```python
>>> class MAC(Field):
...     def __init__(self, default=EUI(0)):
...         super().__init__()
...         self.default = EUI(default)
...
...     def init(self, packet, defaults):
...         obj = defaults.get(self.field_name, self.default)
...         setattr(packet, self.field_name, EUI(obj))
...
...     def pack(self, pkt, fragments, **k):
...         obj = getattr(pkt, self.field_name)
...         fragments.append(obj.packed)
...         return fragments
...
...     def unpack(self, pkt, raw, offset=0, **k):
...         obj = EUI(raw[offset:offset+6].hex())
...         setattr(pkt, self.field_name, obj)
...
...         return offset+6
```

 - nothing changed in `pack` and `unpack`
 - `__init__` and `init` are the same except that we take the object
received from the user and we **ensure** that we store a `EUI` object
calling `EUI(obj)`.

> **Known limitation**: `bisturi` does not support
> [Python Descriptors](https://docs.python.org/3/howto/descriptor.html) for
> `Field` instances at the moment so the user *still can* set any value
> without checking.

Now we can use strings instead of `EUI` objects because it is handy and
also the field will fail if no `EUI` can be created.

```python
>>> class Message(Packet):
...     sender_addr = MAC()
...     receiver_addr = MAC(default='00:50:c2:00:0f:01')

>>> pkt = Message(sender_addr='00:1b:77:49:54:fd')
>>> Message.unpack(pkt.pack())
Message:
  sender_addr: 00-1B-77-49-54-FD
  receiver_addr: 00-50-C2-00-0F-01

>>> pkt.sender_addr = EUI('00:00:00:00:00:00')      # this is a limitation!
>>> pkt.receiver_addr = EUI('ff:ff:ff:ff:ff:ff')

>>> Message.unpack(pkt.pack())
Message:
  sender_addr: 00-00-00-00-00-00
  receiver_addr: FF-FF-FF-FF-FF-FF
```
