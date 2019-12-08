```python
>>> from bisturi.fragments import Fragments

>>> f = Fragments()
>>> f
[]
>>> f.tobytes()
b''

>>> f.append(b'AAA')
>>> f
[(0, b'AAA')]
>>> f.tobytes()
b'AAA'

>>> f.append(b'BBB')
>>> f
[(0, b'AAA'), (3, b'BBB')]
>>> f.tobytes()
b'AAABBB'

>>> f.extend([b'CCC', b'DDD'])
>>> f
[(0, b'AAA'), (3, b'BBB'), (6, b'CCC'), (9, b'DDD')]
>>> f.tobytes()
b'AAABBBCCCDDD'

>>> f.insert(16, b'EEE')
>>> f
[(0, b'AAA'), (3, b'BBB'), (6, b'CCC'), (9, b'DDD'), (16, b'EEE')]
>>> f.tobytes()
b'AAABBBCCCDDD....EEE'


>>> f.insert(12, b'XXX')
>>> f
[(0, b'AAA'), (3, b'BBB'), (6, b'CCC'), (9, b'DDD'), (12, b'XXX'), (16, b'EEE')]
>>> f.tobytes()
b'AAABBBCCCDDDXXX.EEE'

>>> f.append(b'F')
>>> f
[(0, b'AAA'),
 (3, b'BBB'),
 (6, b'CCC'),
 (9, b'DDD'),
 (12, b'XXX'),
 (15, b'F'),
 (16, b'EEE')]
>>> f.tobytes()
b'AAABBBCCCDDDXXXFEEE'

>>> f == b'AAABBBCCCDDDXXXFEEE'
True

>>> f.append(b'ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000010-00000013 when inserting new fragment at 00000010 that span to 00000013

>>> f.insert(2, b'ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000000-00000003 when inserting new fragment at 00000002 that span to 00000005

```

