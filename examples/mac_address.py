from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys

sys.path.append(".")

from bisturi.field import Field, Data
from netaddr import EUI


class MACAddress(Field):
    '''MAC (Ethernet) address using the 'netaddr' lib.
      Two version, the common 48 bits (6 bytes) and the uncommon 64 bits.

      See https://pythonhosted.org/netaddr/api.html.'''
    def __init__(self, version=48, default=None):
        Field.__init__(self)
        self.version = version
        if default is None:
            default = EUI(0, version)
        self.default = default

    def init(self, packet, defaults):
        obj = defaults.get(self.field_name, self.default)
        setattr(packet, self.field_name, EUI(obj, self.version))

    def pack(self, pkt, fragments, **k):
        obj = getattr(pkt, self.field_name)
        fragments.append(obj.packed)
        return fragments

    def unpack(self, pkt, raw, offset=0, **k):
        obj = EUI(raw[offset:offset + 6].hex())
        setattr(pkt, self.field_name, obj)

        return offset + 6


if __name__ == '__main__':
    from bisturi.packet import Packet

    class TestPacket(Packet):
        src = MACAddress(default=EUI("ff:ff:00:00:00:11"))
        dst = MACAddress()

    p1 = TestPacket(dst=EUI("11:11:11:22:22:22"))
    assert p1.pack() == b'\xff\xff\x00\x00\x00\x11\x11\x11\x11\x22\x22\x22'

    p1.dst = EUI('33:33:33:33:33:33')
    assert p1.pack() == b'\xff\xff\x00\x00\x00\x11\x33\x33\x33\x33\x33\x33'

    p2 = TestPacket()
    assert p2.pack() == b'\xff\xff\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00'

    p4 = TestPacket.unpack((p2.pack()))
    assert p4.pack() == b'\xff\xff\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00'
