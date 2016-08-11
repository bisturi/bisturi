
from bisturi.packet import Packet
from bisturi.field  import Int, Data, Bits

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

(?P<hw_type>0001)           # en hexa
(?P<prot_type>0800)
(?P<hw_len>06)
(?P<prot_len>04)
(?P<opcode>0001)
(?P<sender_hw_addr>.{6,6})
(?P<sender_prot_addr>.{4,4})
(?P<target_hw_addr>.{6,6})
(?P<target_prot_addr>.{4,4})


arp = anything_like(ARP) # all fields are Any

(?P<hw_type>.{2,2})
(?P<prot_type>.{2,2})
(?P<hw_len>.{1,1})
(?P<prot_len>.{1,1})
(?P<opcode>.{2,2})
(?P<sender_hw_addr>.*)
(?P<sender_prot_addr>.*)
(?P<target_hw_addr>.*)
(?P<target_prot_addr>.*)


>>> class BitsExample(Packet):
...   type = Int(1)
...   fragment_offset = Bits(12)
...   flags = Bits(4)

bits = BitsExample(type = 1, fragment_offset = 7, flags = Any)

7 == 0000 07xx

          0700
          07ff

(?P<type>01)
(?P<fragment_offset_1>0000)
(?P<fragment_offset_2>[0700-07ff])


bits = BitsExample(type = 1, fragment_offset = Any, flags = 3)

xxxx xx03
     
     0003|0103|0203|....|ff03   # 16 posibilidades, en el pero caso, un byte Any salvo 1 bit da 127 posibilidades

(?P<type>01)
(?P<fragment_offset_1>.{1,1})
(?P<fragment_offset_2>0003|0103|0203|....|ff03)

