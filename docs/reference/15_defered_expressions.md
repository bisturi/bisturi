Several fields accept others fields as parameter to define how many bytes to consume, how many times a fields must be there or if a field should be there or not.

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

>>> str(pkt3.pack()) == raw3
True
>>> str(pkt0.pack()) == '\x00'
True

```

But using only a field as parameter is just the begin. You can use simple expressions as arguments that use one or more fields as operands:

```python
>>> class ArithExpressions(Packet):
...     rows  = Int(1)
...     cols  = Int(1)
...
...     values  = Int(1).repeated(rows * cols)
...     padding = Data( 8 - ((rows * cols) % 8) )

>>> class SequenceExpressions(Packet):
...     items = Int(1).repeated(4)
...     
...     extra_data  = Data(4).when(items[0] == 0xff)
...     hidden_data = Data(4).when(items[:2] == [0xbe, 0xef])

>>> raw_matrix = '\x02\x03ABCDEF\xff\xff'
>>> matrix = ArithExpressions.unpack(raw_matrix)

>>> matrix.rows, matrix.cols
(2, 3)
>>> matrix.values
[65, 66, 67, 68, 69, 70]
>>> matrix.padding
'\xff\xff'

>>> raw_extra_msg = '\xffABCHELO'
>>> extra_msg = SequenceExpressions.unpack(raw_extra_msg)

>>> extra_msg.items
[255, 65, 66, 67]
>>> extra_msg.extra_data
'HELO'
>>> extra_msg.hidden_data is None
True

>>> raw_hidden_msg = '\xbe\xefABbeef'
>>> hidden_msg = SequenceExpressions.unpack(raw_hidden_msg)

>>> hidden_msg.items
[190, 239, 65, 66]
>>> hidden_msg.extra_data is None
True
>>> hidden_msg.hidden_data
'beef'

>>> str(matrix.pack()) == raw_matrix
True

>>> str(extra_msg.pack()) == raw_extra_msg
True
>>> str(hidden_msg.pack()) == raw_hidden_msg
True

```

As a special case, any field or expression of fields implement the 'choose' operator. This one select an item based on the value of the field/expression who owns the operator.
This can be use to select one item from its parameters by position in the argument list or by name from a keyword argument call. If the 'choose' operator receives only one argument, this one can be a list (to select by position) or a dict (to select by keyword).

Here are some examples of using 'choose' by position:

```python
>>> class ChooseExpressions(Packet):
...     a = Int(1)
...     b = Int(1)
...
...     # by position from the argument list
...     extra     = Data(byte_count = 1).when( (a == 1).choose(False, True) )
...
...     # by position but from a list
...     mindata   = Data(byte_count = (a < b).choose([b, a]))
...
...     # by name/keyword from a dictionary (this is the prefered way to 
...     # code a 'if-then-else' expression. Equivalent to: 4 if a > 4 else a 
...     truncated = Data(byte_count = (a > 4).choose({True: 4, False: a}))
...

>>> raw_min = '\x01\x02:AB'
>>> pkt_min = ChooseExpressions.unpack(raw_min)

>>> pkt_min.extra
':'
>>> pkt_min.mindata
'A'
>>> pkt_min.truncated
'B'


>>> raw_trunc = '\x06\x02AABBBBBBBBBBBBBBBB'
>>> pkt_trunc = ChooseExpressions.unpack(raw_trunc)

>>> pkt_trunc.extra is None
True
>>> pkt_trunc.mindata
'AA'
>>> pkt_trunc.truncated
'BBBB'

>>> str(pkt_min.pack()) == raw_min
True
>>> str(pkt_trunc.pack()) == raw_trunc[:8]
True

```

If the pool of names from where you want to choose one is a pool of valid python names you can use keyword arguments as a shortcut instead of an explicit dictionary. 

```python
>>> class ChooseExpressions(Packet):
...     size_type = Data(until_marker='\x00')
...     data      = Data(byte_count = size_type.choose(small=2, large=4, extra_large=8))

>>> raw_small = 'small\x00AB'
>>> pkt_small = ChooseExpressions.unpack(raw_small)

>>> pkt_small.size_type
'small'
>>> pkt_small.data
'AB'

>>> raw_large = 'large\x00ABCD'
>>> pkt_large = ChooseExpressions.unpack(raw_large)

>>> pkt_large.size_type
'large'
>>> pkt_large.data
'ABCD'

>>> str(pkt_small.pack()) == raw_small
True
>>> str(pkt_large.pack()) == raw_large
True

```


