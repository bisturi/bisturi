from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int, Data

class Ethernet(Packet):
   dst_addr = Data(6)
   src_addr = Data(6)
   size     = Int(2)
   payload  = Data(lambda pkt, raw, offset, **k: 
                        pkt.size if pkt.size <= 1500 else (len(raw)-offset))

if __name__ == '__main__':
   from base64 import b16decode
   
   raw_message_empty_payload = b16decode('0018f7f6f7fd00000000000c0000', True)
   raw_message_low_payload = b16decode('0018f7f6f7fd00000000000c000141', True)
   raw_message_high_level_payload = b16decode('0018f7f6f7fd00000000000c0600e11e', True)

   message_empty_payload = Ethernet.unpack(raw_message_empty_payload)
   message_low_payload = Ethernet.unpack(raw_message_low_payload)
   message_high_level_payload = Ethernet.unpack(raw_message_high_level_payload)

   assert message_empty_payload.dst_addr == \
          message_low_payload.dst_addr == \
          message_high_level_payload.dst_addr == \
          b16decode('0018f7f6f7fd', True)

   assert message_empty_payload.src_addr == \
          message_low_payload.src_addr == \
          message_high_level_payload.src_addr == \
          b16decode('00000000000c', True)

   assert message_empty_payload.size == 0
   assert message_empty_payload.payload == b16decode('', True)

   assert message_low_payload.size == 1
   assert message_low_payload.payload == 'A'

   assert message_high_level_payload.size == 1536
   assert message_high_level_payload.payload == b16decode('e11e', True)

