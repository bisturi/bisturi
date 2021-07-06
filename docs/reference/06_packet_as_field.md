# Packet Reference (aka Composite of Packets)

`Int`, `Data` and `Bits` are the key stone from where you can
build complex structures.

`bisturi` allows you to **composite packets** definitions to form
newer and more complex ones.

Consider the following example of an `Ethernet` packet.

```python
>>> from bisturi.field import Data, Int
>>> from bisturi.packet import Packet

>>> class Ethernet(Packet):
...    destination = Data(6)
...    source = Data(6)
...    size = Int(2)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)
```

In `Ethernet`, the `destination` and the `source` are addresses of the
two endpoints talking.

They are `MAC` addresses.

A `MAC` is composed of two parts:

 - the organization identifier `oui`
 - the network controller identifier `nic`.

So we could write a packet that represents a `MAC`:

```python
>>> class MAC(Packet):
...    oui = Data(3)
...    nic = Data(3)
```

Now we can rewrite `Ethernet` **referencing** this `MAC` just using it
in the same place where you would be putting a field:

```python
>>> from bisturi.field import Ref
>>> class Ethernet(Packet):
...    destination = MAC
...    source = MAC
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)
```

Note that I wrote `destination = MAC`: `bisturi` is smart enough
to realice that your are compositing.

Unpacking/packing works as usual: `Ethernet` unpacks/packs its
primitive attributes like  `size` and `payload` and
*delegates* to `MAC` the unpack/pack of `destination` and `source`.

So, we can do this

```python
>>> s1 = b'\x00\x01\x01\x00\x00\x01\x00\x01\x01\x00\x00\x02\x05hello'

>>> p = Ethernet.unpack(s1)

>>> p.destination.nic
b'\x00\x00\x01'
>>> p.source.nic
b'\x00\x00\x02'
>>> p.size
5
>>> p.payload
b'hello'

>>> p.pack() == s1
True
```

Note how you can access to the `nic` field through the `destination` (or
`source`) fields.

<!--
Add an extra test to verify that we can parse a second instance that
will not interfere with the first one.

>>> s2 = b'\x00\x01\x01\x00\x00\x02\x00\x01\x01\x00\x00\x01\x05world'

>>> q = Ethernet.unpack(s2)

>>> q.destination.nic
b'\x00\x00\x02'
>>> q.source.nic
b'\x00\x00\x01'
>>> q.size
5
>>> q.payload
b'world'

>>> q.pack() == s2
True
-->

## Referencing a packet or a field

The `Ref` field accepts either a `Packet` subclass or a `Field` subclass.

Most of the times you will be referencing a `Packet` subclass.

When you do that, the referenced *sub* packet will inherit the same
defaults that the subclass.

If you want to have a different set of defaults, you can pass to `Ref` a
`Packet` *instance*.

```python
>>> class Ethernet(Packet):
...    destination = Ref(MAC(nic=b'\xff\xff\x01'))
...    source = Ref(MAC(nic=b'\xff\xff\x02'))
...    size = Int(1)
...    payload = Data(lambda pkt, raw, offset, **k: pkt.size if pkt.size <= 1500 else len(raw)-offset)

>>> p = Ethernet()
>>>
>>> p.destination.nic
b'\xff\xff\x01'
>>> p.source.nic
b'\xff\xff\x02'
```

As you may noticed, `Ref(MAC)` is just a shortcut for `Ref(MAC())`.

`Ref` is used for creating structured and complex fields. There would be some
occasions where this will not be enough and you will have to create your
own `Field` subclass. But that's for another day.

The `Ref` should **not** be used to link layers or compose unrelated packets.
It is perfectly possible and nobody will prevent to you to do it but it
is a bad practice.

For example, if you have the packet `Ethernet` and the packet `IP`,
you may be tempted to define `Ethernet.payload` as `Ref(IP)` but this will
bind your `Ethernet` implementation to `IP`.

Compositing unrelated packets into a single unit will be cover later.

<!--

Deprecated!

## Inner packet

It is possible to define a `Packet` subclass *inside* another one.

This will make the outer packet to have a reference to the inner packet.
It is just a shortcut for `Ref`:

```python
#   >>> class Person(Packet):
#   ...    length = Int(1)
#   ...    name = Data(length)
#   ...
#   ...    class BirthDate(Packet):
#   ...        day   = Int(1)
#   ...        month = Int(1)
#   ...        year  = Int(2)
#   ...
#   ...    age = Int(1)

#   >>> s = b"\x04john\x05\x03\x07\xda\x16"
#   >>> p = Person.unpack(s)

#   >>> p.length
#   4
#   >>> p.name
#   b'john'
#   >>> p.age
#   22
#   >>> p.birth_date.day    # access the 'BirthDate' field via 'birth_date'
#   5
#   >>> p.birth_date.year
#   2010
```

Notice how the packet's name `BirthDate` has got transformed into
the `birth_date` field.

The rules for renaming follows the *pythonic way*: things like `FooBar`
gets into lowercase and separated by underscores like `foo_bar`.

-->

## Embedded

Sometimes it may feel more natural to access the attributes of a
subpacket without naming the subpacket itself.

Consider the following:

```python
>>> class Frame(Packet):
...    address = Ref(Ethernet, embed=True)

>>> p = Frame()
>>>
>>> p.destination.nic  # direct access, no p.address.destination
b'\xff\xff\x01'
>>> p.source.nic
b'\xff\xff\x02'
```

`embed` makes the referenced subpacket *embedded in* the outer packet:
the fields of the subpacket can be accessed directly.
