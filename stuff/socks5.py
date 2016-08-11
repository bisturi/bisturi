from packet import Packet
from field import Int, Data

#RFC 1928
#socks port 1080
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

class Request(Packet):
   version = Int(1, default=0x05)
   command = Int(1, default=0x01)   #  CONNECT X'01'
                                    #  BIND X'02'
                                    #  UDP ASSOCIATE X'03'
   rsv = Int(1, default=0)
   address_type = Int(1, default=0x03) 
   destination = Data(lambda p: p.destination_length())
   port = Int(2)

   def destination_length(self):
      return {
            0x01: 4,                #  IP V4 address: X'01'
            0x03: 0, # <-- TODO     #  DOMAINNAME: X'03'  
                                       #  TODO: the address field contains a fully-qualified domain name.  The first
                                       #        octet of the address field contains the number of octets of name that
                                       #        follow, there is no terminating NUL octet.
            0x04: 8,                #  IP V6 address: X'04'
            }[self.address_type] 

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
   bound_address = Data(lambda p: p.destination_length())
   bound_port = Int(2)
   
   def destination_length(self):
      return {
            0x01: 4,                #  IP V4 address: X'01'
            0x03: 0, # <-- TODO     #  DOMAINNAME: X'03'  
                                       #  TODO: the address field contains a fully-qualified domain name.  The first
                                       #        octet of the address field contains the number of octets of name that
                                       #        follow, there is no terminating NUL octet.
            0x04: 8,                #  IP V6 address: X'04'
            }[self.address_type] 

