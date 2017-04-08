from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
sys.exit(0)
sys.path.append("../")

from bisturi.field import Field, Data
from netaddr import EUI
import copy

class MACAddress(Field):
   '''MAC (Ethernet) address using the 'netaddr' lib.
      Two version, the common 48 bits (6 bytes) and the uncommon 64 bits.

      See https://pythonhosted.org/netaddr/api.html.'''
   def __init__(self, version=48, default=b"00:00:00:00:00:00"):
      Field.__init__(self)
      self.default = default
      self.version = version
      
   def init(self, packet, defaults):
      self.setval(packet, EUI(defaults.get(self.field_name, self.default), self.version))

   def pack(self, packet):
      return self.getval(packet).packed

   def unpack(self, packet, raw, offset=0):
      addr_as_str = b"-".join(map(lambda b: hex(ord(b))[2:], raw[offset:offset+6]))
      self.setval(packet, EUI(addr_as_str))
   
      return offset+6


if __name__ == '__main__':
   from bisturi.packet import Packet

   class TestPacket(Packet):
      src = MACAddress(default=b"ff:ff:00:00:00:11")
      dst = MACAddress()
     
   p1 = TestPacket(dst=b"11:11:11:22:22:22")
   assert p1.pack() == b'\xff\xff\x00\x00\x00\x11\x11\x11\x11\x22\x22\x22'

   p1.dst = EUI(b'33:33:33:33:33:33')
   assert p1.pack() == b'\xff\xff\x00\x00\x00\x11\x33\x33\x33\x33\x33\x33'

   p2 = TestPacket()
   assert p2.pack() == b'\xff\xff\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00'

   p4 = TestPacket(p2.pack())
   assert p4.pack() == b'\xff\xff\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00'

