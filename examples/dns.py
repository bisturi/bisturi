from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
sys.path.append(".")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Ref, Bkpt

import copy
from enum import Enum, unique

@unique
class ResponseCode(Enum):
    Ok = 0      # No error condition

    FormatError    = 1  # The name server was unable to interpret the query
    ServerFailure  = 2  # The name server was unable to process this query due a problem in the server
    NameError      = 3  # The name referenced in the query doesn't exist (valid for replies form an authoritative server)
    NotImplemented = 4  # The name server does not support the requested kind of query

    Refused = 5 # The server refueses to do something for policy reasons

    # others values are reserved for future use

# RFC 1034, 1035
class Label(Packet):
    length = Int(1)
    #name   = Ref(lambda pkt, **k: Int(1) if pkt.is_compressed() else Data(pkt.length),
    #                default=b'')
    #name = Ref( (length & 0xc0 == 0xc0).choose({True: Int(1), False: Data(length)}), default=b'')
    name  = Data(length).when(length & 0xc0 != 0xc0)
    shift = Int(1).when(length & 0xc0 == 0xc0)

    def is_root(self):
        return self.length == 0

    def is_compressed(self):
        return self.length & 0xc0 == 0xc0

    def offset(self):
        if not self.is_compressed():
            raise Exception()

        return (self.length & (~0xc0) << 8) + self.shift

    def uncompressed_name(self, raw, offset=0):
        if not self.is_compressed():
            return self.name
        else:
            builder = _Builder.unpack(raw, offset=self.offset())
            return b".".join(n.uncompressed_name(raw, offset) for n in builder.name)

class _Builder(Packet):
    name = Ref(Label).repeated(until=lambda pkt, **k: pkt.name[-1].is_root() or pkt.name[-1].is_compressed())

'''
class Name(Packet):
    labels = Ref(Label).repeated(until=lambda pkt, **k: pkt.labels[-1].is_root() or pkt.labels[-1].is_compressed())
    suffix = Ref(Name).at((labels[-1].length & (~0xc0) << 8) + labels[-1].shift).when(labels[-1].is_compressed())
    '''

# from https://www.ietf.org/rfc/rfc1035.txt
class ResourceRecord(Packet):
    name   = Ref(Label).repeated(until=lambda pkt, **k: pkt.name[-1].is_root() or pkt.name[-1].is_compressed())
    type_  = Int(2, default=1)
    class_ = Int(2, default=1)
    ttl    = Int(4)     # time interval that the RR may be cached before the source consult it again. Zero means shouldn't cached (SOA used this)
    length = Int(2)
    data   = Data(length) # (the data varies according type_ and class_)


class Question(Packet):
    name   = Ref(Label).repeated(until=lambda pkt, **k: pkt.name[-1].is_root() or pkt.name[-1].is_compressed())
    type_  = Int(2, default=1)  # the values include all codes valid for this field together with some more general codes
                                # which can match more than one type of resource records
    class_ = Int(2, default=1)  # For example the class_ IN is for the Internet


class Message(Packet):
    id       = Int(2)    # query's id, it's copied in the corresponding reply to match up

    is_query = Bits(1)   # a message can be a query or a reply
    opcode   = Bits(4)

    is_authoritative  = Bits(1) # is an authoritative answer?
    was_truncated     = Bits(1) # was the message truncated due its excessive length?
    request_recursion = Bits(1) # the query desires to be resolved recursively; it's copied in the reply

    is_recursion_available = Bits(1) # is the server supporting recursion? it's set/cleared in the reply
    reserved      = Bits(3)
    response_code = Bits(4)

    qd_count = Int(2)
    an_count = Int(2)
    ns_count = Int(2)
    ar_count = Int(2)

    questions   = Ref(Question).repeated(qd_count)          # the question did in the reply and copied in the response
    answers     = Ref(ResourceRecord).repeated(an_count)    # the answers
    authorities = Ref(ResourceRecord).repeated(ns_count)    # the name servers authorities
    additionals = Ref(ResourceRecord).repeated(ar_count)    # additional records

DNS = Message #alias
'''
ID              A 16 bit identifier assigned by the program that
                generates any kind of query.  This identifier is copied
                the corresponding reply and can be used by the requester
                to match up replies to outstanding queries.

QR              A one bit field that specifies whether this message is a
                query (0), or a response (1).

OPCODE          A four bit field that specifies kind of query in this
                message.  This value is set by the originator of a query
                and copied into the response.  The values are:

                0               a standard query (QUERY)

                1               an inverse query (IQUERY)

                2               a server status request (STATUS)

                3-15            reserved for future use

AA              Authoritative Answer - this bit is valid in responses,
                and specifies that the responding name server is an
                authority for the domain name in question section.

                Note that the contents of the answer section may have
                multiple owner names because of aliases.  The AA bit
                corresponds to the name which matches the query name, or
                the first owner name in the answer section.

TC              TrunCation - specifies that this message was truncated
                due to length greater than that permitted on the
                transmission channel.

RD              Recursion Desired - this bit may be set in a query and
                is copied into the response.  If RD is set, it directs
                the name server to pursue the query recursively.
                Recursive query support is optional.

RA              Recursion Available - this be is set or cleared in a
                response, and denotes whether recursive query support is
                available in the name server.

Z               Reserved for future use.  Must be zero in all queries
                and responses.

RCODE           Response code - this 4 bit field is set as part of
                responses.  The values have the following
                interpretation:

                0               No error condition

                1               Format error - The name server was
                                unable to interpret the query.

                2               Server failure - The name server was
                                unable to process this query due to a
                                problem with the name server.

                3               Name Error - Meaningful only for
                                responses from an authoritative name
                                server, this code signifies that the
                                domain name referenced in the query does
                                not exist.

                4               Not Implemented - The name server does
                                not support the requested kind of query.

                5               Refused - The name server refuses to
                                perform the specified operation for
                                policy reasons.  For example, a name
                                server may not wish to provide the
                                information to the particular requester,
                                or a name server may not wish to perform
                                a particular operation (e.g., zone
                                transfer) for particular data.

                6-15            Reserved for future use.

'''

if __name__ == '__main__':
    from base64 import b16decode

    raw_query = b16decode(b'fabc010000010000000000010377777706676f6f676c6503636f6d00000100010000291000000000000000', True)
    raw_response = b16decode(b'fabc818000010006000400050377777706676f6f676c6503636f6d0000010001c00c000100010000006400044a7d8368c00c000100010000006400044a7d8369c00c000100010000006400044a7d836ac00c000100010000006400044a7d8393c00c000100010000006400044a7d8363c00c000100010000006400044a7d8367c010000200010000016f0006036e7331c010c010000200010000016f0006036e7332c010c010000200010000016f0006036e7334c010c010000200010000016f0006036e7333c010c08c000100010001397d0004d8ef200ac09e000100010000b3600004d8ef220ac0c20001000100010a7a0004d8ef240ac0b0000100010000db710004d8ef260a0000291000000000000000', True)

    query = Message.unpack(raw_query)
    response = Message.unpack(raw_response)

    assert query.id == response.id == 0xfabc

    assert query.opcode == query.is_authoritative == query.was_truncated == query.reserved == query.response_code == 0
    assert response.opcode == response.is_authoritative == response.was_truncated == response.reserved == response.response_code == 0

    assert query.is_query == 0
    assert response.is_query == 1

    assert query.request_recursion == 1 and query.is_recursion_available == 0
    assert response.request_recursion == 1 and response.is_recursion_available == 1

    assert query.qd_count == len(query.questions) == 1
    assert query.an_count == len(query.answers) == 0
    assert query.ns_count == len(query.authorities) == 0
    assert query.ar_count == len(query.additionals) == 1

    assert response.qd_count == len(response.questions) == 1
    assert response.an_count == len(response.answers) == 6
    assert response.ns_count == len(response.authorities) == 4
    assert response.ar_count == len(response.additionals) == 5


    the_question = query.questions[0]
    assert list(map(lambda n: n.name, the_question.name)) == [b'www', b'google', b'com', b'']

    the_question = response.questions[0]
    assert list(map(lambda n: n.name, the_question.name)) == [b'www', b'google', b'com', b'']

    BASE = b"google.com."
    W    = b"www." + BASE
    NS1  = b"ns1." + BASE
    NS2  = b"ns2." + BASE
    NS3  = b"ns3." + BASE
    NS4  = b"ns4." + BASE
    ROOT = b""
    for resource_records, expecteds in zip(
            (response.questions, response.answers, response.authorities, response.additionals),
            ([W], [W]*6, [BASE]*4, [NS1, NS2, NS3, NS4, ROOT])):

        assert len(resource_records) == len(expecteds)
        for one_record, expected_name in zip(resource_records, expecteds):
            labels = one_record.name
            name = b".".join([label.uncompressed_name(raw_response) for label in labels])

            assert name == expected_name

    assert query.pack() == raw_query
    assert response.pack() == raw_response

