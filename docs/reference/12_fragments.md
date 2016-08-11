```python
>>> from bisturi.fragments import Fragments

>>> f = Fragments()
>>> f
[]
>>> str(f)
''

>>> f.append('AAA')
>>> f
[(0, 'AAA')]
>>> str(f)
'AAA'

>>> f.append('BBB')
>>> f
[(0, 'AAA'), (3, 'BBB')]
>>> str(f)
'AAABBB'

>>> f.extend(['CCC', 'DDD'])
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD')]
>>> str(f)
'AAABBBCCCDDD'

>>> f.insert(16, 'EEE')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (16, 'EEE')]
>>> str(f)
'AAABBBCCCDDD....EEE'


>>> f.insert(12, 'XXX')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (12, 'XXX'), (16, 'EEE')]
>>> str(f)
'AAABBBCCCDDDXXX.EEE'

>>> f.append('F')
>>> f
[(0, 'AAA'), (3, 'BBB'), (6, 'CCC'), (9, 'DDD'), (12, 'XXX'), (15, 'F'), (16, 'EEE')]
>>> str(f)
'AAABBBCCCDDDXXXFEEE'

>>> f == 'AAABBBCCCDDDXXXFEEE'
True

>>> f.append('ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000010-00000013 when inserting new fragment at 00000010 that span to 00000013

>>> f.insert(2, 'ZZZ')
Traceback (most recent call last):
Exception: Collision detected with previous fragment 00000000-00000003 when inserting new fragment at 00000002 that span to 00000005

```