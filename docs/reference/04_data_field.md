The Data field is very simple, it is just a piece of bytes.
The interesting part of Data is that its size in bytes can be defined by another field
or it can consume all the string until it find a particular token or a regular expression's match.
Even you can use a function to be called so you can return the size in runtime (unpacking time), but this
will be shown later...

For now, take the following example

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int
>>> import re

>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker='\0')
...    d = Data(until_marker='eof')
...    e = Data(until_marker=re.compile('X+|$'))
...    f = Data(until_marker=re.compile('X+|$'))

```

Let see what happen when the packet is built from this string

```python
>>> s = '\x01abCddd\x00eeeeoffghiXjk'
>>> p = DataExample.unpack(s)
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

```

Note that a sutil problem araises with the delimiters. If the delimiter is a regexp,
there isn't a good default for it. So, be careful with that. The only 'safe' default
is used when the size is fixed:
```python
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

```

If you need that the token be part of the result, you can use the keyword 'include_delimiter'

```python
>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker='\0', include_delimiter=True)
...    d = Data(until_marker='eof', include_delimiter=True)
...    e = Data(until_marker=re.compile('X+|$'), include_delimiter=True)
...    f = Data(until_marker=re.compile('X+|$'), include_delimiter=True)

>>> s = '\x01abCddd\x00eeeeoffghiXjk'
>>> p = DataExample.unpack(s)
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

```

As you can see, when you use a token as delimiter, the token is added to the result.

By default, the until_marker expresion is used to search the marker in the whole raw string
starting from the field's offset which it is quite correct.
But when the raw string is huge or even it is a file, searching in the whole space will require
to load all thoses bytes in memory which can lead to a performance problems.
Fortunely most of the cases we can expect to find the marker in the first few bytes so we can
set a maximum search buffer length to avoid the load of the full string in memory (again, this
makes sense if the raw to be parsed is a file and its content was not loaded into the memory)

Let see an example:

```python
>>> class DataWithSearchLengthLimit(Packet):
...    __bisturi__ = { 'search_buffer_length': 4 }
...
...    a = Data(until_marker='\0', include_delimiter=False)

>>> s = 'ab\x00eeee'
>>> p = DataWithSearchLengthLimit.unpack(s)
>>> p.a
'ab'

```

But if we set a too short buffer and if the marker is not find there, we will get an exception as
if the marker does't exist in the whole string

```python
>>> class DataWithSearchLengthLimitTooShort(Packet):
...    __bisturi__ = { 'search_buffer_length': 2 }
...
...    a = Data(until_marker='\0', include_delimiter=False)

>>> s = 'ab\x00eeee'
>>> p = DataWithSearchLengthLimitTooShort.unpack(s)        # doctest: +ELLIPSIS
Traceback (most recent call last):
...
PacketError: Error when unpacking the field 'a' of packet DataWithSearchLengthLimitTooShort at 00000000...

```

However there As an exception to this limit. Wwhen the search marker is the regex "$" (which means give me to me all 
the rest of the raw string), this regex is honored and will return the rest of the string 
ignoring the search buffer length:

```python
>>> class DataWithSearchLengthLimitTooShortButIgnored(Packet):
...    __bisturi__ = { 'search_buffer_length': 2 }
...
...    a = Data(until_marker=re.compile('$'), include_delimiter=False)

>>> s = 'abeeee'
>>> p = DataWithSearchLengthLimitTooShortButIgnored.unpack(s) 
>>> p.a
'abeeee'

```

So, what happen if we need to compute some non-trivial size that depend on something 
that can be resolved only when the packet disassmble the byte string.
In this case, a callable can be used

```python
>>> class DataExample(Packet):
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size < 255 else len(raw)-offset)

```

or, if you prefer

```python
>>> class DataExample(Packet):
...    def calc_size(pkt, raw, offset, **k):
...       return pkt.size if pkt.size < 255 else len(raw)-offset
...
...    size = Int(1)
...    payload = Data(calc_size)
...

```

In this example, the size of the 'payload' is determined by the value of 'size' only if it 
is not equal to 255. When 'size' is 255, the payload will consume all the bytes until the
end of the packet. 

```python
>>> s1 = '\x01a'
>>> s2 = '\x02ab'
>>> s3 = '\x01abc'
>>> s4 = '\xffa'
>>> s5 = '\xffabc'

>>> DataExample.unpack(s1).payload
'a'
>>> DataExample.unpack(s2).payload
'ab'
>>> DataExample.unpack(s3).payload
'a'
>>> DataExample.unpack(s4).payload
'a'
>>> DataExample.unpack(s5).payload
'abc'

>>> DataExample.unpack(s1).pack() == s1
True
>>> DataExample.unpack(s5).pack() == s5
True

```

But if the length is just a simple expression, we can avoid the use of a callable
writing the expression directly:

```python

>>> class DataWithExpr(Packet):
...    size = Int(1)
...    payload = Data(size * 2)

>>> s1 = '\x01aazzxx'
>>> s2 = '\x02abcdzz'
>>> s3 = '\x01aabb'

>>> DataWithExpr.unpack(s1).payload
'aa'
>>> DataWithExpr.unpack(s2).payload
'abcd'
>>> DataWithExpr.unpack(s3).payload
'aa'

>>> DataWithExpr.unpack(s1).pack() == s1[:-4]
True
>>> DataWithExpr.unpack(s2).pack() == s2[:-2]
True
>>> DataWithExpr.unpack(s3).pack() == s3[:-2]
True

```

