import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int, Data

# See https://www.openssh.com/txt/socks4.protocol
# and https://www.openssh.com/txt/socks4a.protocol

class ClientCommand(object):
    TCP_CONNECTION = 0x01
    TCP_PORT_BIND  = 0x02

    # alias
    CONNECT = TCP_CONNECTION
    BIND    = TCP_PORT_BIND

class ServerStatus(object):
    REQ_GRANTED  = 0x5a
    REQ_REJECTED = 0x5b
    
    CLIENT_NOT_REACHABLE = 0x5c

    INVALID_ID = 0x5d

    # alias
    GRANTED  = REQ_GRANTED
    REJECTED = REQ_REJECTED

    NOT_REACHABLE = CLIENT_NOT_REACHABLE


class ClientHello(Packet):
    version = Int(1, default=0x04)
    command = Int(1, default=ClientCommand.CONNECT) # see ClientCommand

    dst_port = Int(2)
    dst_ip   = Data(4, default='\x00\x00\x00\x01')

    user_id = Data(until_marker='\x00')
    domain_name = Data(until_marker='\x00').when((dst_ip[:3] == '\x00\x00\x00') & (dst_ip[3] != '\x00'))


class ServerHello(Packet):
    version = Int(1, default=0x00)
    status  = Int(1) # see ServerStatus

    dst_port = Int(2)
    dst_ip   = Data(4)

if __name__ == '__main__':
    from base64 import b16decode

    # Example from wikipedia: https://en.wikipedia.org/wiki/SOCKS

    # Socks v4 #################################
    raw_query = b16decode('04 01 0050 42660763 4672656400'.replace(' ', ''), True)
    raw_response = b16decode('00 5a 0050 42660763'.replace(' ', ''), True)

    client_hello = ClientHello.unpack(raw_query)
    server_hello = ServerHello.unpack(raw_response)

    # client -------------------------
    assert client_hello.version == 0x04
    assert client_hello.command == ClientCommand.CONNECT

    ip = '66.102.7.99'
    raw_ip = ''.join(chr(int(octet)) for octet in ip.replace('.', ' ').split())
    assert client_hello.dst_port == 80 and client_hello.dst_ip == raw_ip

    assert client_hello.user_id == 'Fred'
    assert client_hello.domain_name is None

    # server -------------------------
    assert server_hello.version == 0 and server_hello.status == ServerStatus.GRANTED
    assert server_hello.dst_port == 80 and server_hello.dst_ip == raw_ip
    
    # Socks v4a (4a extension) #################
    raw_query = b16decode('04 01 0050 00000001 4672656400 6578616d706c652e636f6d00'.replace(' ', ''), True)

    client_hello = ClientHello.unpack(raw_query)

    # client -------------------------
    assert client_hello.version == 0x04
    assert client_hello.command == ClientCommand.CONNECT

    ip = '0.0.0.1'
    raw_ip = ''.join(chr(int(octet)) for octet in ip.replace('.', ' ').split())
    assert client_hello.dst_port == 80 and client_hello.dst_ip == raw_ip

    assert client_hello.user_id == 'Fred'
    assert client_hello.domain_name == 'example.com'


