There are occasions in we use a parser against a lots of string, parsing even invalid data, with the objective to filter
out and keep only a few strings that are valid and of interest for us.
But instead of unpacking everything like a brute-force attack, we can use a pattern matching technique to
improve the search and filtering.

Imagine the following IP packet (simplified):

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data, Bits, Bkpt

>>> class IP(Packet):
...    version = Bits(4)
...    header_length = Bits(4)
...
...    type_of_service = Int(1)
...    total_length    = Int(2)
...    identification  = Int(2)
...
...    fragment_offset = Bits(13)
...    flags = Bits(3)
...
...    others = Data(4)   # simplification of some fields
...
...    source_address      = Data(4)
...    destination_address = Data(4)
...
...    options = Data(header_length * 4 - 20)   # simplified
...    data    = Data(total_length - header_length * 4)

```


Lets create a pattern that can match any string that it is similar to an IP packet. This doesn't mean that
the string that matches is an IP packet because the pattern only looks loosely some data in the string and
it doesn't check any structure.

We can create this generic pattern with anything_like function:

```python
>>> from bisturi.pattern_matching import anything_like, Any
>>>
>>> ip = anything_like(IP)

```

This will return a normal IP packet, but with a difference, all of its fields has Any as their value.
The Any value is a placeholder for the field and cannot be pack to a string.

```python
>>> isinstance(ip, Packet)
True

```

For debugging we can ask what is the pattern of this incomplete packet

```python
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}.{1}.{1}.{4}.{4}.{4}.*.*'

```

This pattern will match almost anything. Only the small string will not match due the required length of the header.
But we can improve this setting some values. For example if we want to search all the IP packets with a fixed destination
address:

```python
>>> ip.destination_address = "\xff\xff\xff\xff" # broadcast address
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}.{1}.{1}.{4}.{4}\\\xff\\\xff\\\xff\\\xff.*.*'

```

If we want to look for any destination address we set the Any object again

```python
>>> ip.destination_address = Any()
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}.{1}.{1}.{4}.{4}.{4}.*.*'

```

The Bits field can also be set but its regexp is more complex.
If the lower bits of a byte can be any and the higher are fixed, then the regexp will be a range:

  fragment_offset flags
     0000000000111 xxx
     |||||||| \\\\\ \\\
     ||||||||  \\\\\ \\\
     ||||||||   \\\\\ \\\
     00000000    00111 xxx

        0         56-63
      \x00         8-?

```python
>>> ip.fragment_offset = 7
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}\\000[8-\\?].{4}.{4}.{4}.*.*'

```

But if the lower bits are fixed, then we need to try every single bit pattern:

  fragment_offset flags
     xxxxxxxxxxxxx 011
     |||||||| \\\\\ \\\
     ||||||||  \\\\\ \\\
     ||||||||   \\\\\ \\\
     xxxxxxxx    xxxxx 011

       0-256     00000 011 | 00001 011 | 00010 011 | ... | 11111 011
        .                    32 possibilities

```python
>>> ip.fragment_offset = Any()
>>> ip.flags = 3
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}.{1}[\\\x03\\\x0b\\\x13\\\x1b\\#\\+3\\;CKS\\[cks\\{\\\x83\\\x8b\\\x93\\\x9b\\\xa3\\\xab\\\xb3\\\xbb\\\xc3\\\xcb\\\xd3\\\xdb\\\xe3\\\xeb\\\xf3\\\xfb].{4}.{4}.{4}.*.*'

```

Complex, eh?
This is more ease:

  fragment_offset flags
     0000000000111 011
     |||||||| \\\\\ \\\
     ||||||||  \\\\\ \\\
     ||||||||   \\\\\ \\\
     00000000    00111 011
    
         0          59
       \x00          ;

```python
>>> ip.fragment_offset = 7
>>> ip.flags = 3
>>> ip.as_regular_expression().pattern
'(?s).{1}.{1}.{2}.{2}\\000\\;.{4}.{4}.{4}.*.*'

```


Setting a value not only define a fixed string to match for that field but also can change the pattern for others.
For example, the options field depends of the header length. If we set the header length to 5 (5 * 4 = 20 bytes) then
the options field should have 0 bytes. This dependecy is tracked automatically.

```python
>>> ip.fragment_offset = ip.flags = Any()
>>> ip.version = 4
>>> ip.header_length = 5
>>> ip.as_regular_expression().pattern
'(?s)E.{1}.{2}.{2}.{1}.{1}.{4}.{4}.{4}.{0}.*'

```

Notice how the data field depends of both, the header length and the total length and because the last field can
be anything, the data field still has a generic pattern.
Setting the total length to 30 bytes then the data must have room for only 10 bytes

```python
>>> ip.total_length = 30
>>> ip.as_regular_expression().pattern
'(?s)E.{1}\\000\\\x1e.{2}.{1}.{1}.{4}.{4}.{4}.{0}.{10}'

```

Now it's time to do something more useful. In the following data file there are 1210  IP packets, 
all of them of 84 bytes.
Let load the data first.

```python
>>> packet_size  = 84
>>> packet_count = 1210
>>> data = open("pingpattern.data").read()
>>> raw_packets = [data[i*packet_size: (i+1)*packet_size] for i in range(packet_count)]
>>> del data

```

Now we can build a very simple pattern that will match every packet 

```python
>>> ip = anything_like(IP)
>>> ip.version = 4
>>> ip.header_length = 5
>>> ip.total_length = 84

```

With our packet we can filter the raw packets loaded before. The filter uses the pattern
to discard string that are not compatible with the IP structure without parsing the string.

```python
>>> from bisturi.pattern_matching import filter_like
>>> len(list(filter_like(ip, raw_packets))) == packet_count
True

```

This is more fast (two orders) than parsing each string:

```python
>>> import timeit

>>> topt = timeit.Timer(lambda: list(filter_like(ip, raw_packets)))
>>> tgen = timeit.Timer(lambda: [IP.unpack(s) for s in raw_packets])
>>>
>>> best_topt = min(topt.repeat(repeat=1, number=10))
>>> best_tgen = min(tgen.repeat(repeat=1, number=10))

>>> best_topt < best_tgen
True

```

If we want to find a particular packet, then the filter is faster

```python
>>> ip.identification = 0x2fbb
>>> len(list(filter_like(ip, raw_packets))) == 1
True

```

filter_like returns strings that match the pattern and are possible IPs packets
but if we want to be sure we need to unpack the string and do a manual check comparing
the unpacked packet with out target.
The function filter will do that for us and it will return the packets found (objects  not
strings)

```python
>>> import bisturi.pattern_matching as pattern_matching
>>> found = list(pattern_matching.filter(ip, raw_packets))

>>> len(found) == 1
True

>>> isinstance(found[0], IP) and found[0].identification == 0x2fbb
True

```

