import sys
sys.path.append(".")

from bisturi.packet import Packet
from bisturi.field  import Int, Data, Bits

class IPv4(Packet):
    version = Bits(4, default=4)
    header_length = Bits(4, default=5)

    dscp = Bits(6)
    ecn  = Bits(2)

    total_length = Int(2)
    id = Int(2)

    rsv = Bits(1)
    dont_fragment  = Bits(1)
    more_fragments = Bits(1)
    offset = Bits(13)

    ttl = Int(1)
    protocol = Int(1)
    header_checksum = Int(2)

    src = Int(4)
    dst = Int(4)

    options = Data(header_length*4 - 20)
    payload = Data(total_length - (header_length*4))


