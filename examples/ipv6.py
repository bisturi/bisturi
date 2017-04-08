from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Field, Ref, Bkpt

from bisturi.ipaddress import IPv4Address, IPv6Address

import struct
import base64


class len_val(Packet):
   length   = Int(1)
   value    = Data(length)

class Option(Packet):
   type     = Int(1)
   payload  = Ref(len_val).when(type != 0)


class HopByHop(Packet):
   length      = Int(1)
   options     = Ref(Option).repeated(until=lambda pkt, offset, **k: offset > (pkt.length * 8) + 6 + k['local_offset'] )


class Routing(Packet):
   length       = Int(1)
   type         = Int(1)
   segment_left = Int(1)
   options      = Ref(Option).repeated(until=lambda pkt, offset, **k: offset > (pkt.length * 8) + 4 + k['local_offset'])

class IPAddr(Field):
   def __init__(self, version=4, default=None):
      Field.__init__(self)
      if version not in (4, 6):
         raise ValueError('Invalid IP protocol version "%s"' % version)

      self.byte_count = 4 if version == 4 else 16
      self.cls_address = IPv4Address if version == 4 else IPv6Address
      self.default = self.cls_address(default if default is not None else (b'0.0.0.0' if version == 4 else '::'))

   def unpack(self, pkt, raw, offset=0, **k):
      raw_data = raw[offset:offset+self.byte_count]
      
      chunks = [base64.b16encode(raw_data[i:i+2]) for i in range(0, len(raw_data), 2)]
      ip_address = self.cls_address(b":".join(chunks)) # work around for Python 2.7

      setattr(pkt, self.field_name, ip_address)
      return self.byte_count + offset

   def pack(self, packet):
      ip_address = getattr(packet, self.field_name)
      raw = ip_address.packed
      return raw

class Extention(Packet):
   next_header = Int(1)
   val         = Ref(lambda pkt, root, **k: {
                        0: HopByHop(),
                        1: Routing(),
                     }[root.extentions[-1].next_header if root.extentions else root.next_header],
                     default=HopByHop())

class IPv6(Packet):
   version        = Bits(4)
   traffic_class  = Bits(8)
   flow_label     = Bits(20)

   length      = Int(2)
   next_header = Int(1)
   hop_limit   = Int(1)
   src_addr    = IPAddr(version=6)
   dst_addr    = IPAddr(version=6)

   extentions  = Ref(Extention).repeated(until = lambda pkt, **k: pkt.extentions[-1].next_header in (59, 6),
                                           when = lambda pkt, **k: pkt.next_header not in (59, 6))

   payload     = Data(0) # TODO pkt.length-len(pkt.extentions)


if __name__ == '__main__':
   from base64 import b16decode

   # Without extentions neither payload
   raw = b16decode(b'10200003 0000 3b 00 01020304000000000000000000000000 0a0b0000000000000000000000000c0d'.replace(b' ', b''), True)

   ip = IPv6.unpack(raw)

   assert ip.version == 1 and ip.traffic_class == 2 and ip.flow_label == 3
   assert ip.length == 0
   assert ip.next_header == 59
   assert ip.hop_limit == 0
   assert ip.src_addr == IPv6Address(b"0102:0304::")
   assert ip.dst_addr == IPv6Address(b"0a0b::0c0d")

   assert len(ip.extentions) == 0
   assert ip.payload == b""

   # One extention with padding: no options
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b00000000000000'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 6
   
   # One extention with one small option and padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b00 0102aabb 0000'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 3   # one option, two padding

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 2
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aabb", True)
   
   # One extention with one small option and without padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b00 0104aabbccdd'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 1   # one option

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 4
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aabbccdd", True)


   # One extention with one big option and without padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b00 0106aabbccddeeff'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 1   # one option

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 6
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aabbccddeeff", True)
   
   # One extention with two options and without padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b00 0101aa 0101bb'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 2   # two option

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 1
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aa", True)
   assert ip.extentions[0].val.options[1].type == 1
   assert ip.extentions[0].val.options[1].payload.length == 1
   assert ip.extentions[0].val.options[1].payload.value == b16decode(b"bb", True)

   # One big extention with two options and padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 3b01 0103aabbcc 0105aabbccddee 0000'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 1
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 59
   assert ip.extentions[0].val.length == 1   # 1*8 + 6
   assert len(ip.extentions[0].val.options) == 4   # two option plus two padding

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 3
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aabbcc", True)
   assert ip.extentions[0].val.options[1].type == 1
   assert ip.extentions[0].val.options[1].payload.length == 5
   assert ip.extentions[0].val.options[1].payload.value == b16decode(b"aabbccddee", True)
   
   # Three extentions with one option and padding.
   raw = b16decode(b'00000000 0000 00 00 00000000000000000000000000000000 00000000000000000000000000000000 0000 0104aaaaaaaa 0001 0107bbbbbbbbbbbbbb 0000000000 3b00 0102cccc 0000'.replace(b' ', b''), True)
   
   ip = IPv6.unpack(raw)

   assert ip.length == 0
   assert ip.next_header == 0
   assert len(ip.extentions) == 3
   assert ip.payload == b""

   assert isinstance(ip.extentions[0].val, HopByHop)
   assert ip.extentions[0].next_header == 0
   assert ip.extentions[0].val.length == 0
   assert len(ip.extentions[0].val.options) == 1
   assert ip.extentions[1].next_header == 0
   assert ip.extentions[1].val.length == 1
   assert len(ip.extentions[1].val.options) == 6 # one option, 5 padding
   assert ip.extentions[2].next_header == 59
   assert ip.extentions[2].val.length == 0
   assert len(ip.extentions[2].val.options) == 3 # one option, 2 padding

   assert ip.extentions[0].val.options[0].type == 1
   assert ip.extentions[0].val.options[0].payload.length == 4
   assert ip.extentions[0].val.options[0].payload.value == b16decode(b"aaaaaaaa", True)
   assert ip.extentions[1].val.options[0].type == 1
   assert ip.extentions[1].val.options[0].payload.length == 7
   assert ip.extentions[1].val.options[0].payload.value == b16decode(b"bbbbbbbbbbbbbb", True)
   assert ip.extentions[2].val.options[0].type == 1
   assert ip.extentions[2].val.options[0].payload.length == 2
   assert ip.extentions[2].val.options[0].payload.value == b16decode(b"cccc", True)
