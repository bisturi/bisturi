
Now, we need to think, what are the responsabilities of one Field? Well, it has only one:
given a string of bytes create from them a 'python object' and given a 'python object'
return a string of bytes.
This is the only responsability of each Field like Int, Data and Ref.
But what it is this 'python object'? This depends of the Field.
For example, Int can use as its 'python object' an 'int' or a 'long'.
The difference between Int and 'int' is that you are almost always interacting with 'int',
the 'python object' of Int and not with the Int itself.

>>> from field import Int, Field
>>> from packet import Packet
>>> class Ethernet(Packet):
...    size = Int(1)

>>> from field import Field
>>>
>>> isinstance(Ethernet.size, Int)
True
>>> isinstance(Ethernet.size, Field)
True
>>> isinstance(Ethernet.size, (int, long))
False

>>> p = Ethernet()
>>> isinstance(p.size, Int)
False
>>> isinstance(p.size, Field)
False
>>> isinstance(p.size, (int, long))
True

So, when you do something like p.size + 1 you are working with native python objects (int).
No more.
The same happens with Data and Ref.

But Ref is a little more special. He lets you to decide what should be the python object
only if that python object has the methods 'pack' and 'unpack'.
All the packets has them, so they can be used by Ref.

But what happens if we want another type of Field?

For example the 'ip' object from python (IPv4Address and IPv6Address) can be used as that
'python object' but because they don't have the 'pack' neither 'unpack', those classes 
cannot be used as fields using Ref.

So we need to create our own field.

>>> from field import Field
>>> from ipaddress import IPv4Address, IPv6Address
>>> import struct

>>> class IP(Field):
...    def __init__(self, version=4, default='0.0.0.0'):
...       Field.__init__(self)
...       if version not in (4, 6):
...          raise ValueError('Invalid IP protocol version "%s"' % version)
...      
...       self.byte_count = 4 if version == 4 else 16
...       self.cls_address = IPv4Address if version == 4 else IPv6Address
...       self.default = self.cls_address(default)
...    
...    
...    def unpack(self, packet, raw, offset=0):
...       raw_data = raw[offset:offset+self.byte_count]
...       ip_address = self.cls_address(0) # work around for Python 2.7
...       ip_address._ip = struct.unpack(">I", raw_data)[0]
...       self.setval(packet, ip_address)
... 
...       return self.byte_count + offset
... 
...    def pack(self, packet):
...       ip_address = self.getval(packet)
...       raw = ip_address.packed
... 
...       return raw
...

Ok, lets see. 
 - First we inherent from Field. 
 - The constructor __init__ has the expected 'default' keyword and the convenient 'version'.
   With the version as parameter we can handle both version of the IP address schema.
   Two important notes, the parent __init__ is called and the 'default' attribute is setted.
 - Then, the unpack is implemented. We read 4 (or 16) bytes and we set the val interpreted
   using 'setval'. The new offset is returned (the bytes readed plus the old offset).
 - Similar for 'pack'. We get the val using 'getval' and transform the ip address to
   its binary representation which is returned

>>> class IP_Example(Packet):
...    destination = IP(4, '127.0.0.1')
...    source = IP()

>>> p = IP_Example()
>>> isinstance(p.destination, IPv4Address)
True
>>> str(p.destination)
'127.0.0.1'
>>> str(p.source)
'0.0.0.0'
>>> p.pack()
'\x7f\x00\x00\x01\x00\x00\x00\x00'

>>> s = '\xc0\xa8\x01\x01\xc0\xa8\x01\x02'
>>> p.unpack(s)
8
>>> str(p.destination)
'192.168.1.1'
>>> str(p.source)
'192.168.1.2'
>>> p.pack() == s
True

This is really useful because you can use almost any python object and transform it
into a field. The benefice of that is that you can reuse a lot of code already implemented
instead of creation you own objects.
Take a look of the interface of IPv4Address/IPv6Address for free!

>>> p.source.is_loopback
False
>>> p.source.is_private
True
>>> from ipaddress import IPv4Network
>>> p.source in IPv4Network("192.168.0.0/16")
True

Keep this idea. Find some python code that it is useful for you. Then write a small
class to extend Field and thats all!
