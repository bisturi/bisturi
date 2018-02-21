class Methods(object):
    NoAuthenticationRequired = 0x00
    GSSAPI = 0x01
    UserPassword = 0x02

    NotAcceptableMethods = 0xff


class Commands(object):
    Connect = 0x01
    Bind = 0x02
    UDPAssociate = 0x03


class Replies(object):
    Success = 0x00
    GeneralFailure = 0x01

    NotAllowed = 0x02
    NetworkUnreachable = 0x03
    HostUnreachable = 0x04

    ConnectionRefused = 0x05
    TTLExpired = 0x06

    CommandNotSupported = 0x07
    AddressTypeNotSupported = 0x08
    

class AddressType(object):
    IPv4 = 0x01
    DomainName = 0x03
    IPv6 = 0x04


class DomainName(Packet):
    length = Int(1)
    value = Data(length)


class ClientHello(Packet):
    version = Int(1, default=0x05)
    
    num_of_methods = Int(1)
    methods = Int(1).repeated(num_of_methods)


class ServerHello(Packet):
    version = Int(1, default=0x05)
    method = Int(1)


class Request(Packet):
    version = Int(1, default=0x05)
    command = Int(1, default=Commands.Connect)
    
    reserved = Int(1)

    address_type = Int(1, default=AddressType.DomainName)

    dst_address = Ref(lambda pkt, **k: 
                            {
                                AddressType.IPv4: Data(4),
                                AddressType.DomainName: DomainName(),
                                AddressType.IPv6: Data(16),
                            }[pkt.address_type])
    dst_port = Int(2)

class Response(Packet):
    version = Int(1, default=0x05)
    reply = Int(1, default.Replies.Success)

    reserved = Int(1)

    address_type = Int(1, default=AddressType.DomainName)

    bind_address = Ref(lambda pkt, **k: 
                            {
                                AddressType.IPv4: Data(4),
                                AddressType.DomainName: DomainName(),
                                AddressType.IPv6: Data(16),
                            }[pkt.address_type])
    bind_port = Int(2)
