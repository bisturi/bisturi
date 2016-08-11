import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int, Data

# rfc 768
class UDP(Packet):
   src_port = Int(2)
   dst_port = Int(2)
   length   = Int(2)
   checksum = Int(2)

   payload  = Data(lambda pkt, *args: pkt.length-8)


if __name__ == '__main__':
   from base64 import b16decode
   from utils import inspect, hd

   raw_query = b16decode('a4d9003500331c7c' + 'e11e' * 11 * 2, True)
   raw_response = b16decode('0035a4d9010be2fe' + 'e11e' * 65 * 2, True)

   udp_query = UDP()
   udp_query.unpack(raw_query)

   udp_response = UDP()
   udp_response.unpack(raw_response)


   assert udp_query.src_port == udp_response.dst_port == 42201
   assert udp_query.dst_port == udp_response.src_port == 53

   assert udp_query.length == 51
   upper = int((51-8) / 4) + 1
   assert udp_query.payload == b16decode('e11e' * upper * 2, True)[:51-8]
   
   assert udp_response.length == 267
   upper = int((267-8) / 4) + 1
   assert udp_response.payload == b16decode('e11e' * upper * 2, True)[:267-8]

