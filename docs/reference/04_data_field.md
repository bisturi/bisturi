# Data Fields

The `Data` field is very simple: it is just a piece of bytes.

The interesting part is that its size is **not fixed** and it is determined
at run-time.

It can be defined:

 - by the **value of another field**.
 - based on some **pattern** or marker in the data.
 - by a function called in run-time.

## Size based on another field

Let's begin with an example:

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int
>>> import re

>>> class BasedOnOther(Packet):
...    length = Int(1)
...    a = Data(2)
...    b = Data(length)
...    c = Data(length * 2)
```

The field `a` has a *fixed* size of 2 bytes. No much to say.

The interesting fields are `b` and `c` which their sizes depend
on the value of the `length`. As you may guess `b` is a data of
size `length` and `c` is *twice* as large.

        more on expressions         

```python
>>> s = b'\x01abCdd'
>>> p = BasedOnOther.unpack(s)
>>> p.length
1
>>> p.a  # size is fixed to 2 bytes
b'ab'
>>> p.b  # size is the value of 'length' (1 byte in this case)
b'C'
>>> p.c  # size is the value of 'length * 2' (2 bytes in this case)
b'dd'

>>> p.pack() == s
True
```

## Size based on patterns

`Data` fields can also use the same string that it is packing/unpacking
to determinate the size.

With **patterns**, `Data` will consume all the string **until** it finds
a particular token or a regular expression's match.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Int
>>> import re

>>> class BasedOnPattern(Packet):
...    a = Data(until_marker=b'\0', include_delimiter=True)
...    b = Data(until_marker=b'fff')
...    c = Data(until_marker=re.compile(b'X+|$'), include_delimiter=True)
...    d = Data(until_marker=re.compile(b'X+|$'))
```

As you may guess `a` and `b` will read bytes until a `'\0'` and a `'fff'`
are found respectively.

For `c` and `d` the cut condition is based on a regular expression which
in this case says *"until you find one or more X or you reach the end of
the string"*.

```python
>>> s = b'ddd\x00eeeefffghiXXXjk'
>>> p = BasedOnPattern.unpack(s)
>>> p.a  # 'c' will be everything until a '\0' is found (not included)
b'ddd\x00'
>>> p.b  # 'd' is the same, until 'fff' is found (not included)
b'eeee'
>>> p.c  # this uses a regex: "until a 'X' is found or it is the end"
b'ghiXXX'
>>> p.d  # the same, in this case the limit was the end of the string
b'jk'

>>> p.pack() == s
True
```

The fields `a` and `c` have the `include_delimiter` enabled which makes
the fields to include the `until_marker` as part of their content.

For `a` this means include the `'\0'` and for `c` this means include the
`'XXX'`.

### [extra] Searching space

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
limit is **not** honored.

The `$` regex means "give me all until the end of the string". This can
be done very efficiently so there is no need for a limit.

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

## Size based on functions

So, what happen if you need to compute some non-trivial size that
depend on something that can be resolved **only** when the packet
disassembled the byte string?

Just call a function!

```python
>>> class BasedOnFunc(Packet):
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size < 255 else len(raw)-offset)
```

or, if you prefer

```python
>>> class BasedOnFunc(Packet):
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

>>> BasedOnFunc.unpack(s1).payload      # size was 1
b'a'
>>> BasedOnFunc.unpack(s2).payload      # size was 2
b'ab'
>>> BasedOnFunc.unpack(s3).payload      # size was 1
b'a'

>>> s4 = b'\xffa'
>>> s5 = b'\xffabc'

>>> BasedOnFunc.unpack(s4).payload      # size was 255, grab everything
b'a'
>>> BasedOnFunc.unpack(s5).payload      # size was 255, grab everything
b'abc'

>>> BasedOnFunc.unpack(s1).pack() == s1
True
>>> BasedOnFunc.unpack(s5).pack() == s5
True
```


## Defaults for `Data` fields

When `Data` is of fixed size, the default is a string of null bytes
of the size specified.

Otherwise, the default is the empty string. `bisturi` tries to be
pragmatic here: it is not clear what would be a good default for
something non-trivial as `Data(until_marker=re.compile(b'X+|$'))`
so the empty string is as good or bad as another option, but simpler.

```python
>>> q = BasedOnOther()
>>> q.length
0
>>> q.a
b'\x00\x00'
>>> q.b
b''
>>> q.c
b''

>>> q = BasedOnPattern()
>>> q.a
b''
>>> q.b
b''
>>> q.c
b''
>>> q.d
b''
```


        TODO                    
        link to expressions

<!--

Full tests for  `include_delimiter=True`.

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
-->
