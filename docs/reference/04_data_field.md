The `Data` field is very simple: it is just a piece of bytes.

The interesting part is that its size can be defined by another field
or it can be dynamically determined based on some pattern or marker in the
data.

With the pattern, `Data` will consume all the string until it finds
a particular token or a regular expression's match.

Even you can use a function to be called so you can return the size
in runtime (unpacking time), but this will be shown later...

For now, let's focus in the simplest cases:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int
>>> import re

>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker=b'\0')
...    d = Data(until_marker=b'fff')
...    e = Data(until_marker=re.compile(b'X+|$'))
...    f = Data(until_marker=re.compile(b'X+|$'))
```

Let see what happen when the packet is built from this string

```python
>>> s = b'\x01abCddd\x00eeeefffghiXjk'
>>> p = DataExample.unpack(s)
>>> p.length
1
>>> p.a  # size is fixed to 2 bytes
b'ab'
>>> p.b  # size is the value of 'length' (1 byte in this case)
b'C'
>>> p.c  # 'c' will be everything until a '\0' is found (not included)
b'ddd'
>>> p.d  # 'd' is the same, until 'fff' is found (not included)
b'eeee'
>>> p.e  # this uses a regex: "until a 'X' is found or it is the end"
b'ghi'
>>> p.f  # the same, in this case the limit was the end of the string
b'jk'

>>> p.pack() == s
True
```

When `Data` is of fixed size, the default is a string of null bytes.
Otherwise, the default is the empty string (`bisturi` tries to be
pragmatic here).

```python
>>> q = DataExample()
>>> q.length
0
>>> q.a
b'\x00\x00'
>>> q.b
b''
>>> q.c
b''
>>> q.d
b''
>>> q.e
b''
>>> q.f
b''
```

If you need that the token or marker be part of the field value,
set `include_delimiter` to `True`.

```python
>>> class DataExample(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(until_marker=b'\0', include_delimiter=True)
...    d = Data(until_marker=b'fff', include_delimiter=True)
...    e = Data(until_marker=re.compile(b'X+|$'), include_delimiter=True)
...    f = Data(until_marker=re.compile(b'X+|$'), include_delimiter=True)

>>> s = b'\x01abCddd\x00eeeefffghiXjk'
>>> p = DataExample.unpack(s)
>>> p.length
1
>>> p.a
b'ab'
>>> p.b
b'C'
>>> p.c
b'ddd\x00'
>>> p.d
b'eeeefff'
>>> p.e
b'ghiX'
>>> p.f
b'jk'

>>> p.pack() == s
True
```

As you can see, when you use a token as delimiter,
the token is added to the result.

By default, the `until_marker` expression is used to search the marker in
the **whole** raw string starting from the field's offset.

But when the raw string is huge, searching in the whole space may
lead to a performance problems.

Fortunately most of the cases we can expect to find the marker in the first
few bytes so we can set a **maximum search buffer** length to avoid the
scanning of the full string in memory.

Let see an example of `search_buffer_length`:

```python
>>> class DataWithSearchLengthLimit(Packet):
...    __bisturi__ = { 'search_buffer_length': 4 }
...
...    a = Data(until_marker=b'\0')

>>> s = b'ab\x00eeee'
>>> p = DataWithSearchLengthLimit.unpack(s)
>>> p.a
b'ab'
```

If the marker is not found, `bisturi` will not attempt to scan further
and instead it will raise an exception:

```python
>>> class DataWithSearchLengthLimitTooShort(Packet):
...    __bisturi__ = { 'search_buffer_length': 2 }  # tooooo short!
...
...    a = Data(until_marker=b'\0')

>>> s = b'ab\x00eeee'
>>> p = DataWithSearchLengthLimitTooShort.unpack(s)
Traceback (most recent call last):
<...>PacketError: Error when unpacking the field 'a' of packet DataWithSearchLengthLimitTooShort at 00000000<...>
```

There is an exception to this rule: when the marker is the `$` regex the
limit is not honored.

The `$` regex means "give me all until the end of the string". This can
be done very efficiently so there is no need for a limit.

More over, most of the times these kind of fields are for very large
amount of data anyway and a limit is probably useless here.

```python
>>> class DataWithSearchLengthLimitTooShortButIgnored(Packet):
...    __bisturi__ = { 'search_buffer_length': 2 }
...
...    a = Data(until_marker=re.compile(b'$'), include_delimiter=False)

>>> s = b'abeeee'
>>> p = DataWithSearchLengthLimitTooShortButIgnored.unpack(s)
>>> p.a
b'abeeee'
```

        TODO                    
        talke about a shortcut for re.compile(b'$')

So, what happen if we need to compute some non-trivial size that depend on something 
that can be resolved only when the packet disassembled the byte string?

Just call a function!

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

In this example, the size of the `payload` is determined by
the value of `size` only if it is not equal to 255; when `size` is 255,
the payload will consume all the bytes until the end of the packet.

```python
>>> s1 = b'\x01a'
>>> s2 = b'\x02ab'
>>> s3 = b'\x01abc'
>>> s4 = b'\xffa'
>>> s5 = b'\xffabc'

>>> DataExample.unpack(s1).payload      # size was 1
b'a'
>>> DataExample.unpack(s2).payload      # size was 2
b'ab'
>>> DataExample.unpack(s3).payload      # size was 1
b'a'
>>> DataExample.unpack(s4).payload      # size was 255, grab everything
b'a'
>>> DataExample.unpack(s5).payload      # size was 255, grab everything
b'abc'

>>> DataExample.unpack(s1).pack() == s1
True
>>> DataExample.unpack(s5).pack() == s5
True
```

But if the length is just a simple expression, we can avoid
the use of a callable writing the expression directly:

```python
>>> class DataWithExpr(Packet):
...    size = Int(1)
...    payload = Data(size * 2)

>>> s1 = b'\x01aazzxx'
>>> s2 = b'\x02abcdzz'
>>> s3 = b'\x01aabb'

>>> DataWithExpr.unpack(s1).payload     # size of 1, grab 2
b'aa'
>>> DataWithExpr.unpack(s2).payload     # size of 2, grab 4
b'abcd'
>>> DataWithExpr.unpack(s3).payload     # size of 1, grab 2
b'aa'

>>> DataWithExpr.unpack(s1).pack() == s1[:-4]
True
>>> DataWithExpr.unpack(s2).pack() == s2[:-2]
True
>>> DataWithExpr.unpack(s3).pack() == s3[:-2]
True
```

        TODO                    
        link to expressions
