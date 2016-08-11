>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data, Bits


>>> class IP(Packet):
...    version = Bits(4)
...    header_length = Bits(4)
...
...    type_of_service = Int(1)
...    total_length    = Int(2)
...    identification  = Int(2)
...
...    fragment_offset = Bits(13)
...    flags = Bits(3)
...
...    others = Data(4)   # simplification of some fields
...
...    source_address      = Data(4)
...    destination_address = Data(4)
...
...    options = Data(header_length * 4 - 20)   # simplified
...    data    = Data(total_length - (header_length * 4))


Lets create a pattern that can match any string that it is similar to an IP packet. This doesn't mean that
the string that matches is an IP packet because the pattern only looks loosely some data in the string but
it doesn't check any structure.

We can create this generic pattern with anything_like function:

>>> from bisturi.pattern_matching import anything_like
>>>
>>> ip = anything_like(IP)

This will return a normal IP packet, but with a difference, all of its fields has Any as their value.
The Any value is a placeholder for the field and cannot be pack to a string.

>>> isinstance(ip, Packet)
True

For debugging we can ask what is the pattern of this incomplete packet

>>> ip.as_regular_expression().pattern
'.{1}.{1}.{2}.{2}.{1}.{1}.{4}.{4}.{4}.*.*'


(?s)
(?P<version_01>45)
(?P<type_of_service>.{1})
(?P<total_length>.{2})
(?P<identification>.{2})
(?P<fragment_offset_1>.{1})
(?P<fragment_offset_2>.{1})
(?P<others>.{4})
(?P<source_address>.{4})
(?P<destination_address>(?P=source_address))
(?P<options>.{0})
(?P<data>.{,64})



class ARP(Packet):
   hw_type   = Int(2)
   prot_type = Int(2)
   hw_len    = Int(1)
   prot_len  = Int(1)
   opcode    = Int(2)
   
   sender_hw_addr   = Data(hw_len)
   sender_prot_addr = Data(prot_len)
   target_hw_addr   = Data(hw_len)
   target_prot_addr = Data(prot_len)

arp = ARP(hw_type = 0x0001, prot_type = 0x0800,
          hw_len = 6, prot_len = 4, opcode = 1,
          sender_hw_addr = Any, sender_prot_addr = Any,
          target_hw_addr = Any, target_prot_addr = Any)

(?s)
(?P<hw_type>\\000\\\x01)
(?P<prot_type>\\\x08\\000)
(?P<hw_len>\\\x06)
(?P<prot_len>\\\x04)
(?P<opcode>\\000\\\x01)
(?P<sender_hw_addr>.{6})
(?P<sender_prot_addr>.{4})
(?P<target_hw_addr>.{6})
(?P<target_prot_addr>.{4})


arp = anything_like(ARP) # all fields are Any

(?s)
(?P<hw_type>.{2})
(?P<prot_type>.{2})
(?P<hw_len>.{1})
(?P<prot_len>.{1})
(?P<opcode>.{2})
(?P<sender_hw_addr>.*)
(?P<sender_prot_addr>.*)
(?P<target_hw_addr>.*)
(?P<target_prot_addr>.*)


>>> class BitsExample(Packet):
...   type = Int(1)
...   fragment_offset = Bits(12)
...   flags = Bits(4)

bits = BitsExample(type = 1, fragment_offset = 7, flags = Any)

     000000000000 0000
     000000000111 xxxx
     |||||||| \\\\ \\\\
     ||||||||  \\\\ \\\\
     ||||||||   \\\\ \\\\
     00000000    0111 xxxx

        0         112-127
      \x00       \x70-\x7f


(?s)
(?P<type>\\\x01)
(?P<fragment_offset_1>\\000)
(?P<fragment_offset_2>[p-\\\x7f])  # aka "[" + re.escape("\x70") + "-" + re.escape("\x7f") + "]"


bits = BitsExample(type = 1, fragment_offset = Any, flags = 3)

     000000000000 0000
     xxxxxxxxxxxx 0011
     |||||||| \\\\ \\\\
     ||||||||  \\\\ \\\\
     ||||||||   \\\\ \\\\
     xxxxxxxx    xxxx 0011

      0-255      0000 0011 | 0001 0011 | 0010 0011 | ... | 1111 0011
    \x00-\xff               (16 possibilities)

(?s)
(?P<type>\\\x01)
(?P<fragment_offset_1>.{1})
(?P<fragment_offset_2>[\\\x03\\\x13\\\x23\\\x33\\\x43\\\x53\\\x63\\\x73\\\x83\\\x93\\\xa3\\\xb3\\\xc3\\\xd3\\\xe3\\\xf3])


