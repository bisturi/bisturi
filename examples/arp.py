import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int, Data

# RFC  826
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

if __name__ == '__main__':
   from base64 import b16decode

   raw_query = b16decode('00010800060400010018f7f6f7fdc0a80103000000000000c0a8010c', True)
   raw_response = b16decode('0001080006040002002f6f5fdfdfc0a8010c0018f7f6f7fdc0a80103', True)

   arp_query = ARP()
   query_last = arp_query.unpack(raw_query)

   arp_response = ARP()
   response_last = arp_response.unpack(raw_response)


   assert arp_query.hw_type == arp_response.hw_type == 0x0001        # ethernet
   assert arp_query.prot_type == arp_response.prot_type == 0x0800    # ip

   assert arp_query.hw_len == arp_response.hw_len == 6
   assert arp_query.prot_len == arp_response.prot_len == 4

   assert arp_query.sender_hw_addr == arp_response.target_hw_addr == b16decode('0018f7f6f7fd', True)
   assert arp_query.sender_prot_addr == arp_response.target_prot_addr == b16decode('c0a80103', True)

   assert arp_query.target_hw_addr == b16decode('000000000000', True)
   assert arp_response.sender_hw_addr == b16decode('002f6f5fdfdf', True)
   assert arp_query.target_prot_addr == arp_response.sender_prot_addr == b16decode('c0a8010c', True)
