
```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data

>>> class DeferredValue(Packet):
...     number  = Int(1)
...     paylaod = Data(number)
...     elemens = Int(1).repeated(number)
...     msg     = Data(until_marker='\x00').when(number)
...     author  = Data(until_marker='\x00').when(msg)

>>> raw3 = '\x03ABC\x01\x02\x03OK\x00joe\x00'
>>> pkt3  = DeferredValue.unpack(raw3)

>>> pkt3.number
3
>>> pkt3.paylaod
'ABC'
>>> pkt3.elemens
[1, 2, 3]
>>> pkt3.msg
'OK'
>>> pkt3.author
'joe'

>>> raw0 = '\x00ignored\x00'
>>> pkt0 = DeferredValue.unpack(raw0)

>>> pkt0.number
0
>>> pkt0.paylaod
''
>>> pkt0.elemens
[]
>>> pkt0.msg is None
True
>>> pkt0.author is None
True

```

```python
>>> class NaryExpressions(Packet):
...     a = Int(1)
...     b = Int(1)
...
...     data      = Data(byte_count = (a != b).if_true_then_else(( (a*b) + 1, 1)))
...     mindata   = Data(byte_count = (a < b).if_true_then_else((a, b)))
...     truncated = Data(byte_count = (a > 4).if_true_then_else((4, a)))

>>> raw_min = '\x01\x02:::AB'
>>> pkt_min = NaryExpressions.unpack(raw_min)

>>> pkt_min.data
':::'
>>> pkt_min.mindata
'A'
>>> pkt_min.truncated
'B'


>>> raw_trunc = '\x06\x02:::---:::---:AABBBBBBBBBBBBBBBB'
>>> pkt_trunc = NaryExpressions.unpack(raw_trunc)

>>> pkt_trunc.data
':::---:::---:'
>>> pkt_trunc.mindata
'AA'
>>> pkt_trunc.truncated
'BBBB'

```

```python
>>> class ArithExpressions(Packet):
...     rows  = Int(1)
...     cols  = Int(1)

...     values  = Int(1).repeated(rows * cols)
...     padding = Data( 8 - ((rows * cols) % 8) )

```
