# Dynamic Field Definition

So far we have being creating packet classes specifying the field
classes.

But what if a packet's field is not of a *single* type?

In the SOCKS (v5) protocol, one of the packets has the type of
the address used and the address itself.

There are three types of addresses:

 - `IPv4` if `type == 0x01`
 - `IPv6` if `type == 0x04`
 - a *domain name* if `type == 0x03`

The length of the domain name is know from a field that only exists if
`type == 0x03`:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int, Ref

>>> class DomainName(Packet):
...    length = Int(1)
...    name = Data(length)
```

To have a field with a **dynamic type** we need a `Ref` and a callable:

```python
# this is a simplified version of SOCKS, the real one has more
# fields than the shown below
>>> class SOCKS(Packet):
...    type = Int(1, default=0x01)
...    address = Ref(type.chooses({
...                           0x01: Data(4),        # IP v4
...                           0x04: Data(16),       # IP v6
...                           0x03: DomainName(),   # domain name
...                           }),  default=b'\x00\x00\x00\x00')
```

The callable will be executed in runtime and it will select a field
based on `pkt.type`.

The we use `Ref` but instead of referencing a single packet we
use a *callable* to select in runtime to which packet or field
we will reference to.

So, the `address` will be:

 - `Data(4)` (aka `IPv4`) if `type == 0x01`
 - `Data(16)` (aka `IPv6`) if `type == 0x04`
 - `DomainName()`  if `type == 0x03`

Because the object referenced is determined at unpacking time
(using the callable), you need to set a default value explicitly.

Here are some examples, see how `address` is different in each one:

```python
>>> s = b'\x01\x01\x02\x03\x04'
>>> p = SOCKS.unpack(s)
>>> p.type
1
>>> p.address           # IPv4
b'\x01\x02\x03\x04'
>>> p.pack() == s
True

>>> s = b'\x04\x01\x02\x03\x04\x05\x06\x07\x08ABCDEFGH'
>>> p = SOCKS.unpack(s)
>>> p.type
4
>>> p.address           # IPv6
b'\x01\x02\x03\x04\x05\x06\x07\x08ABCDEFGH'
>>> p.pack() == s
True

>>> s = b'\x03\x0bexample.com'
>>> p = SOCKS.unpack(s)
>>> p.type
3
>>> p.address.name      # the domain name
b'example.com'
>>> p.address.length
11
>>> p.pack() == s
True
```

