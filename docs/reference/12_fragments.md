```python
>>> from bisturi.fragments import Fragments

>>> f = Fragments()
>>> f
[]
>>> f.tobytes()
''

>>> f.append(b'AAA')
>>> f
[(0, 'AAA')]
>>> f.tobytes()
'AAA'

>>> f.append(b'BBB')
>>> f
[(0, 'AAA'), (3, 'BBB')]
>>> f.tobytes()
'AAABBB'

>>> f.extend([b'CCC', b'DDD'])
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD')]
>>> f.tobytes()
'AAABBBCCCDDD'

>>> f.insert(16, b'EEE')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (16, 'EEE')]
>>> f.tobytes()
'AAABBBCCCDDD....EEE'


>>> f.insert(12, b'XXX')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (12, 'XXX'), (16, 'EEE')]
>>> f.tobytes()
'AAABBBCCCDDDXXX.EEE'

>>> f.append(b'F')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (12, 'XXX'), (15, 'F'), (16, 'EEE')]
>>> f.tobytes()
'AAABBBCCCDDDXXXFEEE'

>>> f == b'AAABBBCCCDDDXXXFEEE'
True

>>> f.append(b'ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000010-00000013 when inserting new fragment at 00000010 that span to 00000013

>>> f.insert(2, b'ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000000-00000003 when inserting new fragment at 00000002 that span to 00000005

```
