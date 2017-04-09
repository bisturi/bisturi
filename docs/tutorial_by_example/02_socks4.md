Socks4a is the extension of the Socks4 protocol that relays a TCP connection tranparently to the users.

In this protocol the client connect to a Socks server to request him to connect to target server.
The client will send a 'hello' message, a CONNECT (or BIND) request to the server asking him to connect to
a target server (o to bind a address to receive a connection).

Beside the obvious IP address and Port number, the client will send its id, a string that it is delimited by
the null byte.

If the client cannot resolve to which IP wish to connect, it can set it to any IP address of the form 0.0.0.x
and append to the request the domain name to which desire to connect.

So the server must detect the 0.0.0.x pattern and only then try to parse the domain name.

Let's see how to express all this into a bisturi packet class:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class ClientRequest(Packet):
...     version = Int(1, default=0x04)
...     command = Int(1, default=0x01) # a CONNECT request
... 
...     dst_port = Int(2)
...     dst_ip   = Data(4)
... 
...     user_id = Data(until_marker=b'\x00')
...     domain_name = Data(until_marker=b'\x00').when((dst_ip[:3] == b'\x00\x00\x00') & (dst_ip[3] != b'\x00'))

```

Let's read this field by field.

The first two fields are simple, they represent the version and the command or kind of request.

The next two are the port number (a signed, big endian, integer) and 4 bytes for the IP address.

The we have the user's id, an arbitrary string that ends in a null byte. Note how in this case the size of Data
is not defined in terms of a byte count but it will read and consume all the bytes until find the marker, a null byte
in this case.
The until_marker can accept not only a single byte but even a complex regular expression. See the reference of Data for more
examples.

Then, at the end we have the domain_name field which it is a Data field that will read until a null byte. 
But it will read only if the 'when' condition is true. This is an example of a conditional or an optional field.
See 10_callables.md for more information.

This condition can accept a field as an argument or an expression of fields. In order to work this require a little of 
python magic. See 15_defered_expressions.md for more examples and look for the code in deferred.py to see how it works.

But in resume, ```(dst_ip[:3] == b'\x00\x00\x00')``` will compare the first three bytes against three nulls and
```(dst_ip[3] != b'\x00')``` will compare to see if it is distinct of a null byte. Both conditions must be met and
for that reason we use the 'and' operator ```&```

So only when the first three bytes of the IP address are zero and the last byte is different than zero we must
parse the domain name.

Notice how bisturi can handle quite complex rules in simple statements. The idea behind this is to allow to you write
code simple and straight so you can read it later and understand it without reading the RFC or any documentation.

Now let's try to see this in action.
Imagine that you are the server and you received the following byte string:

```python
>>> raw_request = b'\x04\x01\x00\x50\x00\x00\x00\x01gehn\x00github.com\x00'

```

Then you just unpack it:

```python
>>> request = ClientRequest.unpack(raw_request)

>>> request.user_id  # who is?
b'gehn'

>>> request.command # what's he want?
1

>>> request.domain_name # but connect to where?
b'github.com'

>>> request.dst_port
80

```

Now imagine that you receive another request

```python
>>> raw_request = b'\x04\x01\x00\x50\xc0\x1e\xfdpgehn\x00'

```

Then you just unpack it:

```python
>>> request = ClientRequest.unpack(raw_request)

>>> request.user_id  # who is?
b'gehn'

>>> request.command # what's he want?
1

>>> request.domain_name is None # seems that the user already know to which ip to connect
True

>>> request.dst_ip  # let's see the ip then
b'\xc0\x1e\xfdp'

>>> request.dst_port
80

```

To put all this in perspective, let's try to create the same parser but without using bisturi, just using python alone.
It is not so hard, but it easy to screw up with the counters and the sizes.

Ready? Fight!


```python
>>> import struct
>>> def parse_client_request(raw_request):
...     consumed = 0
...     version, command, dst_port, dst_ip = struct.unpack('>BBH4s', raw_request[:1+1+2+4])
...
...     consumed += 1 + 1 + 2 + 4
...     user_id_end = raw_request.find(b'\x00', consumed)
...     user_id = raw_request[consumed:user_id_end]
...
...     consumed += len(user_id) + 1
...     if (dst_ip[:3] == b'\x00\x00\x00') and (dst_ip[3] != b'\x00'):
...         domain_name_end = raw_request.find(b'\x00', consumed)
...         domain_name = raw_request[consumed:domain_name_end]
...
...     else:
...         domain_name = None
...
...     return version, command, dst_port, dst_ip, user_id, domain_name

>>> raw_request = b'\x04\x01\x00\x50\x00\x00\x00\x01gehn\x00github.com\x00'

>>> request = parse_client_request(raw_request)

>>> request[4] # who is?
b'gehn'

>>> request[1] # what's he want?
1

>>> request[5] # but connect to where?
b'github.com'

>>> request[2]
80

```

