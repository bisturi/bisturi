
from packet import Packet
from field import Int, Data

#SOCKS version 4 (and extension 4a)
class ClientHello(Packet):
   version = Int(1, default=0x04)
   command = Int(1, default=0x01) #0x01: tcp connection ; 0x02: tcp port bind
   port = Int(2)
   ip = Data(4, default='\x00\x00\x00\x01')
   user = Data('\x00')
   domain_name = Data(lambda p: '\x00' if p.is_version_4a() else 0)

   def is_version_4a(self):
      return (self.ip[:3] == '\x00\x00\x00' and self.ip[3] != '\x00')


class ServerHello(Packet):
   null = Int(1)
   status = Int(1) #0x5a request granted ; 0x5b rejected ; 0x5c: client not reachable ; 0x5d: invalid id
   port = Int(2)
   ip = Data(4)

