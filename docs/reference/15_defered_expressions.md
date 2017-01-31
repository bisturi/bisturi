
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
