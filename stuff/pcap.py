from packet import Packet
from field import Int, Data

import sys

class MagicNumber(Packet):
   magic_number = Data(4, default='\xa1\xb2\xc3\xd4')
   
   def are_bytes_in_network_order(self):
      return self.magic_number in ('\xa1\xb2\xc3\xd4', '\xa1\xb2\x3c\x4d')


def get_header_and_packet_class(magic_number):
   endianess = 'big' if magic_number.are_bytes_in_network_order() else 'little'

   class Header(Packet):
      major_version = Int(2, endianess=endianess, default=2)
      minor_version = Int(2, endianess=endianess, default=4)
      time_zone_offset = Int(4, endianess=endianess, default=0)
      timestamp_accuracy = Int(4, endianess=endianess, default=0)
      snapshot_length = Int(4, endianess=endianess)
      link_layer_header_type = Int(4, endianess=endianess)

   
   class Packet_(Packet):
      timestamp_approx = Int(4, endianess=endianess)
      timestamp = Int(4, endianess=endianess)
      length = Int(4, endianess=endianess)
      untruncated_length = Int(4, endianess=endianess)
      raw = Data(length)

   return Header, Packet_
