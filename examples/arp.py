import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Field, Ref, Bkpt

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
   from utils import inspect

   raw_query = b16decode('0001000206040000efefefefefef000000001f1f1f1f1f1f00000000', True)
   
   arp_query = ARP()
   arp_query.unpack(raw_query)

   inspect(arp_query)
