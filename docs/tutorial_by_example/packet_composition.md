# Packet Composition

Humans split large problems into smaller chunks and the binary
structures are not the exception.

Network protocols and file formats often define several small packets
and how they compose larger ones.

Considere the [Ethernet
frame](https://en.wikipedia.org/wiki/Ethernet_frame): it is formed by
*"two MAC addresses (6 bytes each), a type (2 bytes) and the payload"*.

```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Data, Bkpt

>>> class File(Packet):
...     __bisturi__ = {}
...
...     # A file name is NULL terminated and may contain slashes
...     # to indicate a folder/subfolders
...     name = Data(until_marker=b'\x00')
...     # so 'size', as read from a tar file, is a string, not a number
...     # hence why we are using Data() instead of Int() or similar
...     mode = Data(8).at(100)
...     owner = Data(8)
...     group = Data(8)
...     size = Data(12)
...     last = Data(12)
...     checksum = Data(8)
...     type = Data(1)
...     linked = Data(100)
...
...     content = Data(lambda pkt, **k: pkt.sz()).when(lambda pkt, **k: not pkt.is_zero()).at(512)
...     _pad2 = Data(lambda pkt, **k: pkt._pad()).when(lambda pkt, **k: not pkt.is_zero() and pkt._pad())
...
...     def is_zero(self):
...         return set(self.size) == {0}
...
...     def sz(self):
...         return int(self.size[:-1], 8)
...
...     def _pad(self):
...         return (256 - int(self.size[:-1], 8) % 256) + 0x100
...
...     def pprint(self):
...         print(f"File: {self.name}")
...         print(f"Size: {self.sz()}")
...         print(f"Mode: {self.mode}")
...         print(f"Group: {self.group}")
...         print(f"Last: {self.last}")
...
...         print()
...         print(self.content[:32])
...         print()

>>> class xFile(Packet):
...     __bisturi__ = {}
...     name = Data(until_marker=b'\x00')
...     mode = Data(8).at(100)
...     owner = Data(8)
...     group = Data(8)
...     size = Data(12)
...     last = Data(12)
...     checksum = Data(8)
...     type = Data(1)
...     linked = Data(100)
...     _pad1 = Data(255)
...
...     content = Data(lambda pkt, **k: pkt.sz()).when(lambda pkt, **k: not pkt.is_zero())
...     _pad2 = Data(lambda pkt, **k: pkt._pad()).when(lambda pkt, **k: not pkt.is_zero() and pkt._pad())
...
...     def is_zero(self):
...         return set(self.size) == {0}
...
...     def sz(self):
...         return int(self.size[:-1], 8)
...
...     def _pad(self):
...         return (256 - int(self.size[:-1], 8) % 256) + 0x100
```

TODO: es un bug tener 2 fields con el mismo nombre, podria Python
avisarnos? Me paso con `_pad1` y `_pad2`

Se necesita una forma no-hack the tracear (prints) y de debuggear

Few comments:

 - the Tar format specifies that the size of the file is a number in
octal using ASCII digits: it is a string, hence we use `int(size, 8)` to
convert it to a real number.

```python
>>> from bisturi import Ref
>>> class TarFile(Packet):
...     files = Ref(File).repeated(until=lambda pkt, **k: pkt.eof())
...
...     def eof(self):
...         return (len(self.files) >= 2 and \
...                 self.files[-1].is_zero() and \
...                 self.files[-2].is_zero())
```

```python
>>> raw = open('tests/ds/onefile.tar', 'rb').read()
>>> tar = TarFile.unpack(raw)   # byexample: +timeout=10

>>> len(tar.files) - 2
1

>>> for f in tar.files[:-2]:
...     f.pprint()
File: b'abc'
Size: 11
Mode: b'0000644\x00'
Group: b'0001750\x00'
Last: b'14406603362\x00'
<...>
b'helloworld\n'
```
