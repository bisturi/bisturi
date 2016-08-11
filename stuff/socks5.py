from packet import Packet
from field import Int, Data, Bits, Ref

#RFC 1928
class ClientHello(Packet):
   version = Int(1, default=0x05)
   num_of_methods = Int(1)
   methods = Data(num_of_methods)

class ServerHello(Packet):
   version = Int(1, default=0x05)
   method = Int(1)      #  X'00' NO AUTHENTICATION REQUIRED
                        #  X'01' GSSAPI
                        #  X'02' USERNAME/PASSWORD
                        #  X'03' to X'7F' IANA ASSIGNED
                        #  X'80' to X'FE' RESERVED FOR PRIVATE METHODS
                        #  X'FF' NO ACCEPTABLE METHODS
                        #
                        #  Compliant implementations MUST support GSSAPI and SHOULD support
                        #  USERNAME/PASSWORD authentication methods.

class _PascalString(Packet):
   length = Int(1)
   val = Data(length)

class Request(Packet):
   version = Int(1, default=0x05)
   command = Int(1, default=0x01)   #  CONNECT X'01'
                                    #  BIND X'02'
                                    #  UDP ASSOCIATE X'03'
   rsv = Int(1, default=0)
   address_type = Int(1, default=0x03) 
   destination = Ref(lambda p: {
      0x01: Data(4),                #  IP V4 address: X'01'
      0x03: _PascalString(),        #  DOMAINNAME: X'03'  
      0x04: Data(8),                #  IP V6 address: X'04'
      }[p.address_type])
   port = Int(2)


class Reply(Packet):
   version = Int(1, default=0x05)
   reply = Int(1)       #  X'00' succeeded
                        #  X'01' general SOCKS server failure
                        #  X'02' connection not allowed by ruleset
                        #  X'03' Network unreachable
                        #  X'04' Host unreachable
                        #  X'05' Connection refused
                        #  X'06' TTL expired
                        #  X'07' Command not supported
                        #  X'08' Address type not supported
                        #  X'09' to X'FF' unassigned

   rsv = Int(1, default=0)
   address_type = Int(1)
   bound_address = Ref(lambda p: {
      0x01: Data(4),                #  IP V4 address: X'01'
      0x03: _PascalString(),        #  DOMAINNAME: X'03'  
      0x04: Data(8),                #  IP V6 address: X'04'
      }[p.address_type])
   bound_port = Int(2)
   

class UDPMessage(Packet):
   rsv = Int(2, default=0x0)
   end_of_fragments = Bits(1)
   fragment_position = Bits(7)
   address_type = Int(1)
   destination = Ref(lambda p: {
      0x01: Data(4),                #  IP V4 address: X'01'
      0x03: _PascalString(),        #  DOMAINNAME: X'03'  
      0x04: Data(8),                #  IP V6 address: X'04'
      }[p.address_type])
   port = Int(2)
   data = Data(Packet.END)
   
   def is_not_fragmented(self):
      return self.end_of_fragments == self.fragment_position == 0
