The Data field is very simple. It is just a piece of bytes.
The interesting part of Data is that its size can be defined by another field
or can be determined by the presence of a token.
In that  case, the Data will consume all the string until it find the token which can
be a simple byte, a more complex string or even a regexp.

>>> from packet import Packet
>>> from field  import Data, Int
>>> import re

>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker='\0')
...    d = Data(until_marker='eof')
...    e = Data(until_marker=re.compile('X+|$'))
...    f = Data(until_marker=re.compile('X+|$'))

Let see what happen when the packet is built from this string

>>> s = '\x01abCddd\x00eeeeoffghiXjk'
>>> p = DataExample(s)
>>> p.length
1
>>> p.a
'ab'
>>> p.b
'C'
>>> p.c
'ddd'
>>> p.d
'eee'
>>> p.e
'fghi'
>>> p.f
'jk'

>>> p.pack() == s
True

Note that a sutil problem is raises with the delimiters. If the delimiter is a regexp,
there isn't a good default for it. So, be careful with that. The only 'safe' default
is used when the size is fixed:

>>> q = DataExample()
>>> q.length
0
>>> q.a
'\x00\x00'
>>> q.b
''
>>> q.c
''
>>> q.d
''
>>> q.e
''
>>> q.f
''


If you need that the token be in the result, you can use the keyword 'include_delimiter'

>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker='\0', include_delimiter=True)
...    d = Data(until_marker='eof', include_delimiter=True)
...    e = Data(until_marker=re.compile('X+|$'), include_delimiter=True)
...    f = Data(until_marker=re.compile('X+|$'), include_delimiter=True)

>>> s = '\x01abCddd\x00eeeeoffghiXjk'
>>> p = DataExample(s)
>>> p.length
1
>>> p.a
'ab'
>>> p.b
'C'
>>> p.c
'ddd\x00'
>>> p.d
'eeeeof'
>>> p.e
'fghiX'
>>> p.f
'jk'

>>> p.pack() == s
True

As you can see, when you use a token as delimiter, the token is added to the result.

A special case arise when the size of the data is not bound to a field only. Instead
depend on something that can be resolved only when the packet disassmble the byte string.
In this case, a callable can be used

>>> class DataExample(Packet):
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size < 255 else len(raw)-offset)

In this example, the size of the 'payload' is determined by the value of 'size' only if it 
is not equal to 255. When 'size' is 255, the payload will consume all the bytes until the
end of the packet.

>>> s1 = '\x01a'
>>> s2 = '\x02ab'
>>> s3 = '\x01abc'
>>> s4 = '\xffa'
>>> s5 = '\xffabc'

>>> DataExample(s1).payload
'a'
>>> DataExample(s2).payload
'ab'
>>> DataExample(s3).payload
'a'
>>> DataExample(s4).payload
'a'
>>> DataExample(s5).payload
'abc'

>>> DataExample(s1).pack() == s1
True
>>> DataExample(s5).pack() == s5
True
