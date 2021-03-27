Now it's time to see how we can create packets from a string
and how we can see a packet as a string of bytes.

First, we create a simple packet class as we did before.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field import Int, Data

>>> class TLP(Packet):
...    type = Int(1)
...    length = Int()
...    payload = Data(length)
```

Now, let be the following string of bytes:

```python
>>> s1 = b'\x02\x00\x00\x00\x03abc'
```

Can you see what should be the value of `type` or `payload`?

I hope!. If not, let the packet **dissect the string** for you
calling `unpack`:

```python
>>> p = TLP.unpack(s1)
>>> p.type
2
>>> p.length
3
>>> p.payload
b'abc'
```

`unpack` optionally receives the offset from where to
start reading.

```python
>>> s2 = b'xxx\x01\x00\x00\x00\x01d'
>>> q = TLP.unpack(s2, offset=3)   #ignore the first 3 bytes "xxx"
>>> q.type
1
>>> q.length
1
>>> q.payload
b'd'
```

Now, if you follow the Python's rules you may ask: *"are the fields
class attributes or instance attributes?"*

They are instance attributes so, as you will expect, two packets
may have different values for the same field.

```python
>>> p.type
2
>>> q.type
1
```

Both are different. Under the hood, those object's attributes are optimized
for use low memory and the packets don't have a `__dict__` instance.

```python
>>> hasattr(p, '__dict__')
False
```

The reverse of `unpack()` is, obviously, `pack()`: make a packet into
a sequence of bytes:

```python
>>> p.pack() == s1
True
>>> q.pack() == s2[3:]
True
```


## Error handling

If a field cannot be unpacked, an exception is raised with the full
stack of packets and offsets:

```python
>>> def some_function(raw):
...    q = TLP.unpack(raw)

>>> s = b'\x00\x00\x00\x00\x04a'
>>> some_function(s)
Traceback (most recent call last):
<...>PacketError: Error when unpacking the field 'payload' of packet TLP at 00000005: Unpacked 1 bytes but expected 4
Packet stack details:
    00000005 TLP                            .payload
Field's exception:
<...>
Exception: Unpacked 1 bytes but expected 4<...>
```

The same is true if the packet cannot be packed into a string:

```python
>>> p = TLP()
>>> p.length = "a non integer!"

>>> p.pack()
Traceback (most recent call last):
<...>PacketError: Error when packing the field 'between 'type' and 'length'' of packet TLP at 00000000: <...> argument <...> integer
Packet stack details:
    00000000 TLP                            .between 'type' and 'length'
Field's exception:
<...>
```

There will be more about debugging, errors and unpacking/packing invalid data
but for now this is enough.

## Working with files

No always you will have the full string in memory to parse
but you will have a file instead.

`SeekableFile` adapter will make the file behave as a string so
`bisturi` can use it.

```python
>>> from bisturi.util import SeekableFile

>>> seekable_file = SeekableFile(open('tests/ds/tlp_abc', 'rb'))

>>> p = TLP.unpack(seekable_file)
>>> p.length
3
>>> p.payload
b'abc'
```

