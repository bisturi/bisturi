In the SOCKS (v5) protocol, one of the packets has the type of the address used and the 
address itself (the SOCKS packet has more fields but they aren't relevant in this case).

If the type is 0x01, the address is an IP v4, if it is 0x04 is an IP v6.
This seems to be simple:

>>> from packet import Packet
>>> from field  import Data, Int

>>> class SOCKS(Packet):
...    type = Int(1, default=0x01)
...    address = Data(lambda p: {
...                           0x01: 4,    # IP v4
...                           0x04: 8,    # IP v6
...                           }[p.type])

But the protocol define another address's type: 0x03, the address is a domain name.
The problem is that the domain name has the first byte as the size of the domain name.
If you see the packet above, how can we know the size of the domain?
How we can know the size of the address before read it and at the same time we need to read
its first byte to know the length of the address?!

We need a more generic solution and the old Ref is the indicate.
We can define very quickly the parser if the domain name (this way to encode
a string is the same used by the language Pascal) and the use it with Ref.
The trick is that Ref not only can reference Packets as Fields, 
he can dynamically reference to a Packet or another Field using a callable.

>>> from field  import Data, Int, Ref

>>> class NData(Packet):
...    length = Int(1)
...    data = Data(length)

>>> class SOCKS(Packet):
...    type = Int(1, default=0x01)
...    address = Ref(lambda p: {
...                           0x01: Data(4),    # IP v4
...                           0x04: Data(8),    # IP v6
...                           0x03: NData(),    # domain name
...                           }[p.type])

So, depends on the value of 'type', 'address' will be a Ref to a Data (a Field) or
to a NData (a Packet)

>>> s = '\x01\x01\x02\x03\x04'
>>> p = SOCKS(s)
>>> p.type
1
>>> p.address.val
'\x01\x02\x03\x04'
>>> p.pack() == s
True

>>> s = '\x04\x01\x02\x03\x04\x05\x06\x07\x08'
>>> p = SOCKS(s)
>>> p.type
4
>>> p.address.val
'\x01\x02\x03\x04\x05\x06\x07\x08'
>>> p.pack() == s
True

>>> s = '\x03\x0bexample.com'
>>> p = SOCKS(s)
>>> p.type
3
>>> p.address.data
'example.com'
>>> p.address.length
11
>>> p.pack() == s
True

Note that when Ref is referencing to a Field, the address (the value of the field) has
one level of indirection and to access to this value, the attribute 'val' must be used.
When Ref is referencing a Packet, the same level of indirection exists but the names
of the attributes are the same that were defined in the Packet.

