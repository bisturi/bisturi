from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
sys.path.append(".")

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


class ClientRequest(Packet):
    version = Int(1, default=0x04)
    command = Int(1, default=ClientCommand.CONNECT) # see ClientCommand

    dst_port = Int(2)
    dst_ip   = Data(4, default=b'\x00\x00\x00\x01')

    user_id = Data(until_marker=b'\x00')
    domain_name = Data(until_marker=b'\x00').when((dst_ip[:3] == b'\x00\x00\x00') & (dst_ip[3] != b'\x00'))


class ServerResponse(Packet):
    version = Int(1, default=0x00)
    status  = Int(1) # see ServerStatus

    dst_port = Int(2)
    dst_ip   = Data(4)

if __name__ == '__main__':
    from base64 import b16decode

    # Example from wikipedia: https://en.wikipedia.org/wiki/SOCKS

    # Socks v4 #################################
    raw_request = b16decode(b'04 01 0050 42660763 4672656400'.replace(b' ', b''), True)
    raw_response = b16decode(b'00 5a 0050 42660763'.replace(b' ', b''), True)

    client_request = ClientRequest.unpack(raw_request)
    server_response = ServerResponse.unpack(raw_response)

    # client -------------------------
    assert client_request.version == 0x04
    assert client_request.command == ClientCommand.CONNECT

    ip = b'66.102.7.99'
    raw_ip = b''.join(chr(int(octet)) for octet in ip.replace(b'.', b' ').split())
    assert client_request.dst_port == 80 and client_request.dst_ip == raw_ip

    assert client_request.user_id == b'Fred'
    assert client_request.domain_name is None

    # server -------------------------
    assert server_response.version == 0 and server_response.status == ServerStatus.GRANTED
    assert server_response.dst_port == 80 and server_response.dst_ip == raw_ip
    
    assert client_request.pack() == raw_request
    assert server_response.pack() == raw_response

    # Socks v4a (4a extension) #################
    raw_request = b16decode(b'04 01 0050 00000001 4672656400 6578616d706c652e636f6d00'.replace(b' ', b''), True)

    client_request = ClientRequest.unpack(raw_request)

    # client -------------------------
    assert client_request.version == 0x04
    assert client_request.command == ClientCommand.CONNECT

    ip = b'0.0.0.1'
    raw_ip = b''.join(chr(int(octet)) for octet in ip.replace(b'.', b' ').split())
    assert client_request.dst_port == 80 and client_request.dst_ip == raw_ip

    assert client_request.user_id == b'Fred'
    assert client_request.domain_name == b'example.com'

    assert client_request.pack() == raw_request

