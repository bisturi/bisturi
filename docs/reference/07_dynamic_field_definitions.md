In the SOCKS (v5) protocol, one of the packets has the type of
the address used and the address itself.

In SOCKS you can use IPv4 and IPv6 addresses which are signaled as
`type == 0x01` and `type == 0x04` respectively.

As we saw before we can set the address length dynamically using
a function to return 4 (for IPv4) and 8 (for IPv6) depending of the
value of `type`

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int

>>> # this is a simplified version of SOCKS, the real one has more
... # fields than the shown below
>>> class SOCKS(Packet):
...    type = Int(1, default=0x01)
...    address = Data(lambda pkt, **k: {
...                           0x01: 4,    # IP v4
...                           0x04: 8,    # IP v6
...                           }[pkt.type])
```

The protocol defines another value for `type` (`0x03`): the address is *not*
and instead should be interpreted as *a domain name*.

The problem is that the domain name is fundamentally different from just
a bunch of bytes (like the ones that `Data` models).

It has some structure: the first byte as the size of the domain name and
then it follows the domain name.

So what we need to do is not change the size of `address` dynamically
but *change the field type* itself.

Here is where `Ref` plays a critical role.

First we need to model a domain name:

```python
>>> class DomainName(Packet):
...    length = Int(1)
...    name = Data(length)
```

The we use `Ref` but instead of referencing a single packet we
use a *callable* to select in runtime to which packet or field
we will reference to.

```python
>>> from bisturi.field import Ref

>>> class SOCKS(Packet):
...    type = Int(1, default=0x01)
...    address = Ref(lambda pkt, **k: {
...                           0x01: Data(4),        # IP v4
...                           0x04: Data(8),        # IP v6
...                           0x03: DomainName(),   # domain name
...                           }[pkt.type],  default=b'\x00\x00\x00\x00')
```

So, the `address` type depends on the value of `type`: for values
of `0x01` and `0x04` `Ref` will reference a `Data` *field*, for
a value of `0x03` `Ref` will reference a `DomainName` *packet*.

Because the object referenced is determined at unpacking time
(using the callable), you need to set a default value.

```python
>>> s = b'\x01\x01\x02\x03\x04'
>>> p = SOCKS.unpack(s)
>>> p.type
1
>>> p.address
b'\x01\x02\x03\x04'
>>> p.pack() == s
True

>>> s = b'\x04\x01\x02\x03\x04\x05\x06\x07\x08'
>>> p = SOCKS.unpack(s)
>>> p.type
4
>>> p.address
b'\x01\x02\x03\x04\x05\x06\x07\x08'
>>> p.pack() == s
True

>>> s = b'\x03\x0bexample.com'
>>> p = SOCKS.unpack(s)
>>> p.type
3
>>> p.address.name
b'example.com'
>>> p.address.length
11
>>> p.pack() == s
True
```

