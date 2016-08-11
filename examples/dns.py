import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Field, Ref

import copy

class CompressedName(Packet):
   flags  = Bits(2)
   offset = Bits(14)

class NotCompressedName(Packet):
   class Label(Packet):
      length = Int(1)
      name   = Data(length)

   partial_names = Ref(Label).repeated(until=lambda pkt, *args: pkt.partial_names[-1].length == 0)

class DomainName(Field):
   def __init__(self, default=NotCompressedName()):
      Field.__init__(self)
      self.default = default

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, copy.deepcopy(self.default)))

   def unpack(self, packet, raw, offset=0):
      we_have_only_one_byte = len(raw[offset:]) == 1

      if we_have_only_one_byte:
         compressed = False
         partial_name = NotCompressedName()
         new_offset = partial_name.unpack(raw, offset)
         assert partial_name.length == 0
      else:
         partial_name = CompressedName()   # assume that is compressed, for now
         new_offset = partial_name.unpack(raw, offset)
         if partial_name.flags == 0b00:
            partial_name = NotCompressedName() # it wasn't compressed!
            new_offset = partial_name.unpack(raw, offset)

         elif partial_name.flags == 0b11:
            #ok, it is compressed
            pass
         else:
            raise NotImplementedError()

      self.setval(packet, partial_name)
      return new_offset
   
   def pack(self, packet):
      partial_name = self.getval(packet)
      return partial_name.pack()
         

class ResourceRecord(Packet):
   name   = DomainName()
   type_  = Int(2, default=1)
   class_ = Int(2, default=1)
   ttl    = Int(4)
   length = Int(2)
   data   = Data(length)

'''
(from https://www.ietf.org/rfc/rfc1035.txt)

NAME            an owner name, i.e., the name of the node to which this
                resource record pertains.

TYPE            two octets containing one of the RR TYPE codes.

CLASS           two octets containing one of the RR CLASS codes.

TTL             a 32 bit signed integer that specifies the time interval
                that the resource record may be cached before the source
                of the information should again be consulted.  Zero
                values are interpreted to mean that the RR can only be
                used for the transaction in progress, and should not be
                cached.  For example, SOA records are always distributed
                with a zero TTL to prohibit caching.  Zero values can
                also be used for extremely volatile data.

RDLENGTH        an unsigned 16 bit integer that specifies the length in
                octets of the RDATA field.

RDATA           a variable length string of octets that describes the
                resource.  The format of this information varies
                according to the TYPE and CLASS of the resource record.
'''

class Question(Packet):
   qname  = DomainName()
   qtype  = Int(2, default=1)
   qclass = Int(2, default=1)

'''
QNAME           a domain name represented as a sequence of labels, where
                each label consists of a length octet followed by that
                number of octets.  The domain name terminates with the
                zero length octet for the null label of the root.  Note
                that this field may be an odd number of octets; no
                padding is used.

QTYPE           a two octet code which specifies the type of the query.
                The values for this field include all codes valid for a
                TYPE field, together with some more general codes which
                can match more than one type of RR.

QCLASS          a two octet code that specifies the class of the query.
                For example, the QCLASS field is IN for the Internet.
'''

class Message(Packet):
   id       = Int(2)

   qr       = Bits(1)
   opcode   = Bits(4)
   aa       = Bits(1)
   tc       = Bits(1)
   rd       = Bits(1)
   ra       = Bits(1)
   reserved = Bits(3)
   rcode    = Bits(4)

   qd_count = Int(2)
   an_count = Int(2)
   ns_count = Int(2)
   ar_count = Int(2)

   questions   = Ref(Question).repeated(qd_count)
   answers     = Ref(ResourceRecord).repeated(an_count)
   authorities = Ref(ResourceRecord).repeated(ns_count)
   additionals = Ref(ResourceRecord).repeated(ar_count)

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

QDCOUNT         an unsigned 16 bit integer specifying the number of
                entries in the question section.

ANCOUNT         an unsigned 16 bit integer specifying the number of
                resource records in the answer section.

NSCOUNT         an unsigned 16 bit integer specifying the number of name
                server resource records in the authority records
                section.

ARCOUNT         an unsigned 16 bit integer specifying the number of
                resource records in the additional records section.
'''
# TODO agregar una forma de debuggear el parseo, field a field.
if __name__ == '__main__':
   from base64 import b16decode
   from utils import inspect

   raw_query = b16decode('fabc010000010000000000010377777706676f6f676c6503636f6d00000100010000291000000000000000', True)
   raw_response = b16decode('fabc818000010006000400050377777706676f6f676c6503636f6d0000010001c00c000100010000006400044a7d8368c00c000100010000006400044a7d8369c00c000100010000006400044a7d836ac00c000100010000006400044a7d8393c00c000100010000006400044a7d8363c00c000100010000006400044a7d8367c010000200010000016f0006036e7331c010c010000200010000016f0006036e7332c010c010000200010000016f0006036e7334c010c010000200010000016f0006036e7333c010c08c000100010001397d0004d8ef200ac09e000100010000b3600004d8ef220ac0c20001000100010a7a0004d8ef240ac0b0000100010000db710004d8ef260a0000291000000000000000', True)

   query = Message(raw_query)
   response = Message()

   response.unpack(raw_response)


   assert query.id == response.id == 0xfabc
   
   assert query.opcode == query.aa == query.tc == query.reserved == query.rcode == 0
   assert response.opcode == response.aa == response.tc == response.reserved == response.rcode == 0

   assert query.qr == 0
   assert response.qr == 1

   assert query.rd == 1 and query.ra == 0
   assert response.rd == 1 and response.rd == 1
   
   assert query.qd_count == len(query.questions) == 1
   assert query.an_count == len(query.answers) == 0
   assert query.ns_count == len(query.authorities) == 0
   assert query.ar_count == len(query.additionals) == 1
   
   assert response.qd_count == len(response.questions) == 1
   assert response.an_count == len(response.answers) == 6
   assert response.ns_count == len(response.authorities) == 4
   assert response.ar_count == len(response.additionals) == 5
   

   the_question = query.questions[0]
   assert list(map(lambda n: n.name, the_question.qname.partial_names)) == ['www', 'google', 'com', '']

   the_question = response.questions[0]
   assert list(map(lambda n: n.name, the_question.qname.partial_names)) == ['www', 'google', 'com', '']
 
   # TODO more tests!
   #position_of_first_partial_name = raw_query.find('www')
   #print query.additionals[0].name.offset, position_of_first_partial_name
   #assert query.additionals[0].name.offset == position_of_first_partial_name

