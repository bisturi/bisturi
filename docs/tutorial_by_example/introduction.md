# Introduction

Imagine that you need to parse a binary structure. It can be a network
packet, a binary file in your disk or whatever other binary blob you can
think.

Parsing it is tedious and error prone. Python offers `struct` but
it falls short for non-trivial tasks.

`bisturi` is a library to build a parser and a serializer for your
packets describing them in a *declarative way*.

An example may explain better.

Considere the [Address Resolution
Protocol](https://en.wikipedia.org/wiki/Address_Resolution_Protocol)
packet or ARP for short.

It consists of *"the hardware and the protocol type (2 bytes each),
the hardware and protocol addresses' length (1 byte each), an opcode (2
bytes), the sender's hardware and protocol addresses and the target's
(receiver's) hardware and protocol addresses; the length in bytes
of each hardware and protocol addresses are defined by the previously
defined hardware and protocol addresses' length."*

We can translate almost 1-to-1 the description of ARP into a single
`bisturi` packet definition:


```python
>>> from bisturi.packet import Packet
>>> from bisturi.field  import Int, Data

>>> class ARP(Packet):
...     hw_type   = Int(2)
...     prot_type = Int(2)
...     hw_len    = Int(1)
...     prot_len  = Int(1)
...     opcode    = Int(2)
...
...     sender_hw_addr   = Data(hw_len)
...     sender_prot_addr = Data(prot_len)
...     target_hw_addr   = Data(hw_len)
...     target_prot_addr = Data(prot_len)
```


That means `bisturi` is *declaratative*: You just declare the fields of
the packets and `bisturi` will create the parser for you behind the
scenes.

## Packet's fields

Let's inspect the `ARP` packet:

 - first, a `Packet` subclass is created.
 - for each field we created a *class attribute* of type `Int` or
`Data`.
 - each `Int` field represents an integer and receives the length in
bytes. So `hw_type = Int(2)` means an integer field named `hw_type` of 2
bytes.
 - each `Data` field represents a binary blob and like `Int` it receives
the length of the field in bytes.

You probably noticed that `Data` receives not a number but another
field.

Remember from the definition of ARP:

*The length in bytes
of each hardware and protocol addresses are defined by the previously
defined hardware and protocol addresses' length."*

So each address has a length defined by *another* field.

`bisturi` automatically resolves `sender_hw_addr = Data(hw_len)` in
runtime, parses `hw_len` first and its (integer) value is used as the
length of `sender_hw_addr`.

Magic? Let me show you a more interesting example.

## Fields expressions

Imagine that you have to read from a binary file a `Matrix`, a classic
bidimensional vector/array.

The format says *"the count of rows and columns (1 byte each) are
followed by the values of the matrix, rows times columns integers
of 1 byte each; the whole structure is padded to a multiple of 8."*

```python
>>> class Matrix(Packet):
...     rows  = Int(1)
...     cols  = Int(1)
...
...     values  = Int(1).repeated(rows * cols)
...     padding = Data( 8 - ((rows * cols) % 8) ).when(((rows * cols) % 8))
```

Let's review it:

 - `rows` and `cols` are two integers of 1 byte each (`Int(1)`).
 - `values` is a *single* integer of 1 byte (`Int(1)`) that it is
*repeated* `rows` times `cols`: `values` is a **list** of integers.
 - `padding` is just a blob of length `8 - ((rows * cols) % 8)` (the
bytes needed to complete an 8-bytes block). But the padding is defined
*only when* the block is not multiple the 8 (`when(((rows * cols) % 8))`)

This example may give you an idea of the expressiveness of `bisturi`.

## Packing and unpacking

Like any other Python class, you can instantiate your packets:

```python
>>> arp1 = ARP()  # initialize it with reasonable defaults
>>> arp1
ARP:
  hw_type: 0
  prot_type: 0
  hw_len: 0
  prot_len: 0
  opcode: 0
  sender_hw_addr: b''
  sender_prot_addr: b''
  target_hw_addr: b''
  target_prot_addr: b''
```

You can change the defaults during the packet creation
or later via a normal attribute set:

```python
>>> arp2 = ARP(opcode=42)  # custom setting
>>> arp2
ARP:
  <...>
  opcode: 42
  <...>

>>> arp2.opcode = 57
>>> arp2
ARP:
  <...>
  opcode: 57
  <...>
```

`bisturi` builds a parser and a serializer for your packets: the parser
takes a binary *raw* string of bytes and *unpacks* it creating a new
packet object; the serializer takes your packet object and *packs* into a
binary string.

```python
>>> raw = arp2.pack()
>>> raw
b'\x00\x00\x00\x00\x00\x00\x009'

>>> arp3 = ARP.unpack(raw)
>>> arp3
ARP:
  hw_type: 0
  prot_type: 0
  hw_len: 0
  prot_len: 0
  opcode: 57
  sender_hw_addr: b''
  sender_prot_addr: b''
  target_hw_addr: b''
  target_prot_addr: b''
```

This is the packing/unpacking of `Matrix`:

```python
>>> m1 = Matrix(rows=2, cols=3, values=[1, 2, 3, 4, 5, 6], padding=b'..')
>>> m1
Matrix:
  rows: 2
  cols: 3
  values: [1, 2, 3, 4, 5, 6]
  padding: b'..'

>>> raw = m1.pack()
>>> raw
b'\x02\x03\x01\x02\x03\x04\x05\x06..'

>>> m2 = Matrix.unpack(raw)
>>> m2
Matrix:
  rows: 2
  cols: 3
  values: [1, 2, 3, 4, 5, 6]
  padding: b'..'
```

## Packet consistency

`bisturi` is quite relaxed and does not enforce a type
checking, basically you could set an incorrect
opcode like `arp2.opcode = None`.

`bisturi` does not check the consistency between your fields either.

For example we could create a matrix that it is *not* padded to 8:

```python
>>> m3 = Matrix(rows=2, cols=3, values=[1, 2, 3, 4, 5, 6])
>>> m3
Matrix:
  rows: 2
  cols: 3
  values: [1, 2, 3, 4, 5, 6]
  padding: None
```

As long as `bisturi` can work without trouble, it will not complain.

This *relaxed* design is specifically to support *crafting of malformed*
packets.

```python
>>> raw = m3.pack()
>>> raw
b'\x02\x03\x01\x02\x03\x04\x05\x06'
```

But `bisturi` is very *strict* when parsing:

```python
>>> m4 = Matrix.unpack(raw)             # byexample: +norm-ws
Traceback (most recent call last):
<...>
bisturi.packet.PacketError: Error when unpacking the field 'padding' of
packet Matrix at 00000008: Unpacked 0 bytes but expected 2
Packet stack details:
    00000008 Matrix                         .padding
<...>
```

A packet *consistency* can be asserted if you want:

```python
>>> m1.assert_consistency()
True

>>> m3.assert_consistency()
Traceback (most recent call last):
<...>
bisturi.packet.PacketError: <...>

>>> m3.assert_consistency(dont_raise=True)
False
```
