from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import time, struct, sys, copy, re

from bisturi.packet import Packet, Prototype
from bisturi.deferred import defer_operations, UnaryExpr, BinaryExpr, NaryExpr,\
                                    compile_expr_into_callable
from bisturi.pattern_matching import Any
from bisturi.fragments import FragmentsOfRegexps
from bisturi.util import to_bytes

from bisturi.six import integer_types, from_int_to_byte

def exec_once(m):
    ''' Force to execute the method m only once and save its result.
        The next calls will always return the same result,
        ignoring the parameters. '''
    def wrapper(self, *args, **kargs):
        try:
            return getattr(self, "_%s_cached_result" % m.__name__)
        except AttributeError as e:
            r = m(self, *args, **kargs)
            setattr(self, "_%s_cached_result" % m.__name__, r)
            return r

    return wrapper

class Field(object):
    ''' A field represent a single parsing unit. This is the superclass from
        where all the other field must inherit.

        A field will hold a raw configuration from it initialization (__init__)
        until the compilation of it (_compile method).
        Once you call _compile, the field will define the most optimum version
        for its pack and unpack methods.

        See the Packet class to get a more broad view about this.

        Any field instance will support the following public methods besides the
        pack/unpack:
            - repeated: to define a sequence of fields like Int(1).repeated(4)
              (see the Sequence field).
            - when: to define a field as optional like Int(1).when(foo == True)
              (see the Optional field).
            - at: to define where the field should start to pack/unpack
              (see the Move field).
            - aligned: a variant of at.

            '''
    def __init__(self):
        self.ctime = time.time()
        self.is_fixed = False
        self.struct_code = None
        self.is_bigendian = True

        self.move_arg = None
        self.movement_type = None

        self.descriptor = None
        self.descriptor_name = None

    def _describe_yourself(self, field_name, bisturi_conf):
        ''' Given a name and a configuration, set the name of this field
            and return the list of tuples that describe this field.
            Each tuple contains the name of the field and the value of the
            field.

            The most simple case is a description that consists in a list of one
            tuple
                [(my name, myself)]
            but it is possible that a field requires more than one tuple to
            describe.
            For example, Int(1).at(x) requires two tuples one about the movement
            (at) and the other about the int itself like:
                [(my move's name, Move(x)), (my name, myself)]
            '''
        from bisturi.structural_fields import Move

        self.field_name = field_name
        if self.move_arg is None and 'align' in bisturi_conf:
            self.aligned(to=bisturi_conf['align'])

        if self.descriptor:
            self.descriptor_name = field_name

            # The original field name will be used by the descriptor. We (field)
            # use a hidden field name instead
            self.field_name = "_described_%s" % field_name
            field_name = self.field_name

            # Notify to the descriptor both attribute names
            self.descriptor.descriptor_name = self.descriptor_name
            self.descriptor.real_field_name = self.field_name


        if self.move_arg is None:
            return [(field_name, self)]

        else:
            m = Move(self.move_arg, self.movement_type)
            m.field_name = "_shift_to_%s" % field_name
            return [(m.field_name, m), (field_name, self)]

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        ''' Realize all the optimizations available and return a list of names
            which will be the __slots__ of the packet class. This is the time
            to realize all the optimizations in terms of speed and memory as
            you can. '''
        # Dont call this from a subclass. Call _compile_impl directly.
        return self._compile_impl(position, fields, bisturi_conf)

    def _compile_impl(self, position, fields, bisturi_conf):
        slots = [self.field_name]
        if self.descriptor:
            slots.append(self.descriptor_name)

        return slots

    def init(self, packet, defaults):
        ''' Initialize the field based on the default.
            This must set a 'field_name' attribute in the packet.'''
        try:
            obj = defaults[self.field_name]
        except KeyError:
            obj = copy.deepcopy(self.default)

        setattr(packet, self.field_name, obj)

    def unpack(self, pkt, raw, offset, **k):
        raise NotImplementedError()

    def pack(self, pkt, fragments, **k):
        raise NotImplementedError()

    def unpack_noop(self, pkt, raw, offset, **k):
        ''' No-operation unpack function. Do nothing during the
            unpacking stage. '''
        return offset

    def pack_noop(self, pkt, fragments, **k):
        ''' No-operation pack function. Do nothing during the packing stage. '''
        return fragments

    def repeated(self, count=None, until=None, when=None, default=None,
                                                                aligned=None):
        r''' The sequence can be set to a fixed amount of elements with the
            'count' parameter which can be a number, a field, an expression of
            fields or even an arbitrary callable.
            In any case the parameter must be resolved to a positive integer.

            In the other hand, the sequence can set an 'until' condition.
            In this case the sequence will stop only when the until condition
            gives a true value.

            The 'count' and the 'until' parameter are exclusive: one and only
            one of them must be set.

            The 'when' condition can be used to make the whole sequence
            optional. If the when condition is not met, the sequence will be
            resolved to an empty list.

            >>> from bisturi.packet import Packet
            >>> from bisturi.field  import Int, Data, Ref

            >>> class Bag(Packet):
            ...     num = Int(1)
            ...     objects = Int(1).repeated(num)

            >>> class Box(Packet):
            ...     bags = Ref(Bag).repeated(until=lambda pkt, **k: pkt.bags[-1].num == 0)

            >>> pkt = Box(bags=[Bag(num=1, objects=[2]), Bag()])
            >>> len(pkt.bags)
            2
            >>> [(bag.num, bag.objects) for bag in pkt.bags]
            [(1, [2]), (0, [])]

            >>> pkt.pack() == b'\x01\x02\x00'
            True

            >>> raw = b'\x02\x01\x02\x01\x04\x00'
            >>> pkt = Box.unpack(raw)

            >>> len(pkt.bags)
            3
            >>> [(bag.num, bag.objects) for bag in pkt.bags]
            [(2, [1, 2]), (1, [4]), (0, [])]

            >>> pkt.pack() == raw
            True

            The 'aligned' parameter control how the elements of the sequence are
            packed (aligned) one each other.

            >>> class Room(Packet):
            ...     tight = Ref(Box).repeated(2, default=[Box(bags=[Bag()]), Box(bags=[Bag()])])
            ...     no_so_tight = Ref(Box).repeated(2, aligned=6, default=[Box(bags=[Bag()]), Box(bags=[Bag()])])

            >>> pkt = Room()
            >>> [sum((bag.objects for bag in box.bags), []) for box in pkt.tight]
            [[], []]
            >>> [sum((bag.objects for bag in box.bags), []) for box in pkt.no_so_tight]
            [[], []]

            >>> pkt.pack() == b'\x00\x00....\x00.....\x00'
            True

            >>> raw = b'\x01A\x00\x02BC\x00.....\x01A\x00...\x02BC\x00'
            >>> pkt = Room.unpack(raw)

            >>> [sum((bag.objects for bag in box.bags), []) for box in pkt.tight]
            [[65], [66, 67]]
            >>> [sum((bag.objects for bag in box.bags), []) for box in pkt.no_so_tight]
            [[65], [66, 67]]

            >>> pkt.pack() == raw
            True

            '''
        from bisturi.structural_fields import Sequence
        return Sequence(prototype=self, count=count, until=until, when=when,
                                            default=default, aligned=aligned)

    def when(self, condition, default=None):
        r''' A field can be set as optional based on a 'when' condition.
             This one can be a field, an expression of fields or an arbitrary
             callable that resolves to a boolean value: True if the field must
             be parsed or False otherwise.

             If a field is not parsed, None is used a the value for that field.

             The 'when' condition has no effect in a default packet neither
             during the packing phase.

             >>> from bisturi.packet import Packet
             >>> from bisturi.field  import Int, Data, Ref

             >>> class Example(Packet):
             ...     type = Int(1)
             ...     nonzero_msg = Data(2).when(type)
             ...     typeone_msg = Data(2).when(type == 1)

             >>> pkt = Example(nonzero_msg=b'X') # notice how all the fields are set...
             >>> (pkt.type, pkt.nonzero_msg, pkt.typeone_msg) # the when is ignored
             (0, 'X', None)

             >>> pkt.nonzero_msg = b'AB'
             >>> pkt.typeone_msg = b'CD'
             >>> pkt.pack() == b'\x00ABCD' # the when is ignored here too
             True

             >>> raw = b'\x00AB'
             >>> pkt = Example.unpack(raw) # here when is honored (both field...
             >>> (pkt.type, pkt.nonzero_msg, pkt.typeone_msg) # aren't parsed)
             (0, None, None)

             >>> pkt.pack() == b'\x00'
             True

             >>> raw = b'\x02AB'
             >>> pkt = Example.unpack(raw)
             >>> (pkt.type, pkt.nonzero_msg, pkt.typeone_msg)
             (2, 'AB', None)

             >>> raw = b'\x01ABCD'
             >>> pkt = Example.unpack(raw)
             >>> (pkt.type, pkt.nonzero_msg, pkt.typeone_msg)
             (1, 'AB', 'CD')

             >>> pkt.pack() == raw
             True

             '''

        from bisturi.structural_fields import Optional
        return Optional(prototype=self, when=condition, default=default)

    def at(self, position, movement_type='absolute'):
        self.move_arg = position
        self.movement_type = movement_type
        return self

    def aligned(self, to, local=False):
        self.move_arg = to
        self.movement_type = 'align-local' if local else 'align-global'
        return self

    def pack_regexp(self, pkt, fragments, **k):
        raise NotImplementedError("The pack_regexp method is not implemented for this field.")

    def describe(self, descriptor):
        self.descriptor = descriptor
        return self



@defer_operations(allowed_categories=['integer'])
class Int(Field):
    def __init__(self, byte_count=4, signed=False, endianness=None, default=0):
        Field.__init__(self)
        self.default = default
        self.byte_count = byte_count
        self.endianness = endianness
        self.is_signed = signed
        self.is_fixed = True

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)

        if self.endianness is None:
            # try to get the default from the Packet class; big endian
            # by default
            self.endianness = bisturi_conf.get('endianness', 'big')

        self.is_bigendian = (self.endianness in ('big', 'network')) or \
                            (self.endianness == 'local' and sys.byteorder == 'big')

        if self.byte_count in (1, 2, 4, 8):
            code = {1:'B', 2:'H', 4:'I', 8:'Q'}[self.byte_count]
            if self.is_signed:
                code = code.lower()

            self.struct_code = code
            fmt = (">" if self.is_bigendian else "<") + code
            self.struct_obj = struct.Struct(fmt)

            self.pack, self.unpack = self._pack_fixed_and_primitive_size, \
                                        self._unpack_fixed_and_primitive_size

        else:
            self.struct_code = None
            self.base = 2**(self.byte_count*8)

            self.pack, self.unpack = self._pack_fixed_size, \
                                        self._unpack_fixed_size

        return slots

    def init(self, packet, defaults):
        setattr(packet, self.field_name, defaults.get(self.field_name,
                                                                self.default))
    def unpack(self, pkt, raw, offset=0, **k):
        raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

    def pack(self, pkt, fragments, **k):
        raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

    def _unpack_fixed_and_primitive_size(self, pkt, raw, offset=0, **k):
        next_offset = offset + self.byte_count
        integer = self.struct_obj.unpack(raw[offset:next_offset])[0]
        setattr(pkt, self.field_name, integer)

        return next_offset

    def _pack_fixed_and_primitive_size(self, pkt, fragments, **k):
        integer = getattr(pkt, self.field_name)
        raw = self.struct_obj.pack(integer)
        fragments.append(raw)

        return fragments

    def _unpack_fixed_size(self, pkt, raw, offset=0, **k):
        next_offset = offset + self.byte_count
        raw_data = raw[offset:next_offset]

        try:
            num = int.from_bytes(raw_data,
                        byteorder='big' if self.is_bigendian else 'little',
                        signed=self.is_signed)

        except AttributeError:
            if not self.is_bigendian:
                raw_data = raw_data[::-1]

            hexbytes = raw_data.encode('hex')
            num = int(hexbytes, 16)

            if self.is_signed and ord(raw_data[0]) > 127:
                num = -(self.base - num)

        setattr(pkt, self.field_name, num)
        return next_offset

    def _pack_fixed_size(self, pkt, fragments, **k):
        integer = getattr(pkt, self.field_name)

        try:
            data = integer.to_bytes(self.byte_count,
                            byteorder='big' if self.is_bigendian else 'little',
                            signed=self.is_signed)

        except AttributeError:
            num = (self.base + integer) if integer < 0 else integer

            xcode = "%%0%(count)ix" % {'count': self.byte_count*2}
            data = (xcode % num).decode('hex')

            if not self.is_bigendian:
                data = data[::-1]

        fragments.append(data)
        return fragments

    def pack_regexp(self, pkt, fragments, **k):
        value = getattr(pkt, self.field_name)
        is_literal = not isinstance(value, Any)

        if is_literal:
            self.pack(pkt, fragments, **k)
        else:
            fragments.append((".{%i}" % self.byte_count).encode('ascii'),
                                                            is_literal=False)

        return fragments

@defer_operations(allowed_categories=['sequence'])
class Data(Field):
    def __init__(self, byte_count=None, until_marker=None,
            include_delimiter=False, consume_delimiter=True, default=b''):
        Field.__init__(self)
        assert (byte_count is None and until_marker is not None) or \
                (until_marker is None and byte_count is not None)

        if until_marker is not None:
            if hasattr(until_marker, 'search'): # aka regex
                pattern = until_marker.pattern
                if not isinstance(pattern, bytes):
                    raise ValueError("The until marker is a regular expression which pattern is of type '%s' but it must be 'bytes'." % type(pattern))
            else:
                if not isinstance(until_marker, bytes):
                    raise ValueError("The until marker must be 'bytes' or a regular expression, not '%s'." % type(until_marker))

        if not isinstance(default, bytes):
            raise ValueError("The default must be 'bytes' not '%s'." %
                                                                type(default))

        self.default = default
        if not default and isinstance(byte_count, integer_types):
            self.default = b"\x00" * byte_count

        self.byte_count = byte_count
        self.until_marker = until_marker

        self.include_delimiter = include_delimiter
        self.delimiter_to_be_included = (self.until_marker if
                isinstance(self.until_marker, bytes) and not include_delimiter
                else b'')

        assert not (consume_delimiter == False and include_delimiter == True)
        self.consume_delimiter = consume_delimiter #XXX document this!
        self.is_fixed = isinstance(byte_count, integer_types)

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)

        if self.byte_count is not None:
            if isinstance(self.byte_count, integer_types):
                self.struct_code = "%is" % self.byte_count
                self.unpack = self._unpack_fixed_size

            elif isinstance(self.byte_count, Field):
                self.unpack = self._unpack_variable_size_field

            elif callable(self.byte_count):
                self.unpack = self._unpack_variable_size_callable

            elif isinstance(self.byte_count, (UnaryExpr, BinaryExpr, NaryExpr)):
                self.byte_count = compile_expr_into_callable(self.byte_count)
                self.unpack = self._unpack_variable_size_callable

            else:
                assert False

        else:
            self._search_buffer_length = bisturi_conf.get('search_buffer_length')
            if self._search_buffer_length is not None:
                # the length can be 0 or None (means infinite) or a positive number
                assert self._search_buffer_length >= 0

            if isinstance(self.until_marker, bytes):
                self.unpack = self._unpack_with_string_marker

            elif hasattr(self.until_marker, 'search'):
                self.unpack = self._unpack_with_regexp_marker

            else:
                assert False

        return slots

    def init(self, packet, defaults):
        setattr(packet, self.field_name, defaults.get(self.field_name,
                                                                self.default))

    def unpack(self, pkt, raw, offset=0, **k):
        raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

    def pack(self, pkt, fragments, **k):
        r = getattr(pkt, self.field_name) + self.delimiter_to_be_included
        fragments.append(r)
        return fragments

    def _unpack_fixed_size(self, pkt, raw, offset=0, **k):
        byte_count = self.byte_count
        next_offset = offset + byte_count

        chunk = raw[offset:next_offset]
        if len(chunk) != byte_count:
            raise Exception("Unpacked %i bytes but expected %i" %
                                                    (len(chunk), byte_count))

        setattr(pkt, self.field_name, chunk)
        return next_offset

    def _unpack_variable_size_field(self, pkt, raw, offset=0, **k):
        byte_count = getattr(pkt, self.byte_count.field_name)
        next_offset = offset + byte_count

        chunk = raw[offset:next_offset]
        if len(chunk) != byte_count:
            raise Exception("Unpacked %i bytes but expected %i" %
                                                    (len(chunk), byte_count))

        setattr(pkt, self.field_name, chunk)
        return next_offset

    def _unpack_variable_size_callable(self, pkt, raw, offset=0, **k):
        byte_count = self.byte_count(pkt=pkt, raw=raw, offset=offset, **k)
        next_offset = offset + byte_count

        chunk = raw[offset:next_offset]
        if len(chunk) != byte_count:
            raise Exception("Unpacked %i bytes but expected %i" %
                                                    (len(chunk), byte_count))

        setattr(pkt, self.field_name, chunk)
        return next_offset

    def _unpack_with_string_marker(self, pkt, raw, offset=0, **k):
        until_marker = self.until_marker

        if self._search_buffer_length:
            max_next_offset_allowed = offset + self._search_buffer_length
            search_buffer = raw[offset:max_next_offset_allowed]
        else:
            search_buffer = raw[offset:]

        count = search_buffer.find(until_marker)
        assert count >= 0

        extra_count = 0
        if self.include_delimiter:
            count += len(until_marker)
        else:
            self.delimiter_to_be_included = until_marker
            if self.consume_delimiter:
                extra_count = len(until_marker)

        next_offset = offset + count
        setattr(pkt, self.field_name, raw[offset:next_offset])

        return next_offset + extra_count

    def _unpack_with_regexp_marker(self, pkt, raw, offset=0, **k):
        until_marker = self.until_marker

        if self._search_buffer_length:
            max_next_offset_allowed = offset + self._search_buffer_length
            search_buffer = raw[offset:max_next_offset_allowed]
        else:
            search_buffer = raw[offset:]

        extra_count = 0
        if until_marker.pattern == b"$":    # shortcut
            count = len(raw) - offset
        else:
            match = until_marker.search(search_buffer, 0) #XXX should be (raw, offset) or (raw[offset:], 0) ? See the method search in the module re
            if match:
                if self.include_delimiter:
                    count = match.end()
                else:
                    count = match.start()
                    if self.consume_delimiter:
                        extra_count = match.end()-count
                    self.delimiter_to_be_included = match.group()
            else:
                assert False

        next_offset = offset + count
        setattr(pkt, self.field_name, raw[offset:next_offset])

        return next_offset + extra_count

    def pack_regexp(self, pkt, fragments, **k):
        value = getattr(pkt, self.field_name)
        is_literal = not isinstance(value, Any)

        if is_literal:
            self.pack(pkt, fragments, **k)

        else:
            custom_regexp = (value.regexp.pattern if value.regexp is not None
                                                  else b".*")
            if self.byte_count is not None:
                if isinstance(self.byte_count, integer_types):
                    byte_count = self.byte_count

                elif isinstance(self.byte_count, Field):
                    byte_count = getattr(pkt, self.byte_count.field_name)

                elif callable(self.byte_count):
                    try:
                        byte_count = self.byte_count(pkt=pkt, **k)
                    except Exception as e:
                        byte_count = None

                if byte_count is not None:
                    # TODO ignoring the custom regexp!!
                    fragments.append((".{%i}" % byte_count).encode('ascii'),
                                                            is_literal=False)
                else:
                    fragments.append(custom_regexp, is_literal=False)

            else:
                endswith = (re.escape(self.until_marker) if
                                        isinstance(self.until_marker, bytes)
                                        else self.until_marker.pattern)
                fragments.append(custom_regexp + endswith, is_literal=False)

        return fragments

class Ref(Field):
    r'''Reference to another packet description. This field allows to composite
        different packet descriptions.

        The prototype parameter must be a packet class, a packet instance or a
        callable.
        If it is the latter, the callable must return a packet instance or a
        field instance each time that it is called.
        Because of that, the callable must to return a new packet/field instance
        each time, you cannot return the same object twice.

        The callable will be called during the unpack stage but it can also be
        called during the pack stage to determinate how to pack a value when
        this one is not a packet instance (let's say that you are referencing to
        an Int field and I have the value 42, I need to call the callable to
        get an Int instance to pack the 42).
        In this case the callable will be call with the parameter packing=True.

        If the prototype is a packet, then the default it is not needed becasue
        we can use the prototype as a default value for the field.
        But if it is a callable, the default is mandatory otherwise we cannot
        know how to create a default value for the field.

        >>> from bisturi.packet import Packet
        >>> from bisturi.field  import Int, Data, Ref

        >>> class Point(Packet):
        ...     x = Int(1)
        ...     y = Int(1)

        >>> class Line(Packet):
        ...     begin = Ref(Point(x=1, y=2)) # prototype is used as the default
        ...     end   = Ref(Point) # shortcut for Ref(Point())
        ...
        ...     extra = Ref(lambda **k: Point(), default=Point(y=7)) # default is mandatory

        >>> pkt = Line()
        >>> (pkt.begin.x, pkt.begin.y)
        (1, 2)
        >>> (pkt.end.x, pkt.end.y)
        (0, 0)
        >>> (pkt.extra.x, pkt.extra.y)
        (0, 7)

        >>> pkt.pack() == b'\x01\x02\x00\x00\x00\x07'
        True

        >>> raw = b'\x01\x02\x03\x04\x05\x06'
        >>> pkt = Line.unpack(raw)

        >>> (pkt.begin.x, pkt.begin.y)
        (1, 2)
        >>> (pkt.end.x, pkt.end.y)
        (3, 4)
        >>> (pkt.extra.x, pkt.extra.y)
        (5, 6)

        >>> pkt.pack() == raw
        True


        If the embeb parameter is True, the prototype must be a packet.
        With this flag all the fields of the prototype are borrow to the
        current packet.
        The embeb feature is quite experimental and has a few quirks:

        >>> class Point3D(Packet):
        ...     point_2d = Ref(Point(x=1, y=2), embeb=True)
        ...     z = Int(1)

        >>> pkt = Point3D(x=7)
        >>> (pkt.x, pkt.y, pkt.z) # XXX this should be (7, 2, 0) but...
        (7, 0, 0)

        >>> pkt.x = 8
        >>> pkt.point_2d.y = 9
        >>> pkt.pack() == b'\x08\x00\x00' # XXX but it should be 08 09 00
        True

        >>> raw = b'\x01\x02\x03'
        >>> pkt = Point3D.unpack(raw)
        >>> (pkt.x, pkt.y, pkt.z)
        (1, 2, 3)

        >>> pkt.pack() == b'\x01\x02\x03'
        True

        '''

    def __init__(self, prototype, default=None, embeb=False,
                                            _is_a_subpacket_definition=False):
        Field.__init__(self)

        if _is_a_subpacket_definition:
            self.ctime = prototype.get_fields()[0][1].ctime

        self.default = default

        if isinstance(prototype, type):
            # get an object, this allows write Ref(PacketClass)
            # instead of Ref(PacketClass())
            prototype = prototype()

        if not isinstance(prototype, Packet) and not callable(prototype) and \
                not isinstance(prototype, (UnaryExpr, BinaryExpr, NaryExpr)):
            raise ValueError("The prototype of a Ref field must be a packet (class or instance), an expression of fields or a callable that should return a Field or a Packet.")

        self._lets_find_a_nice_default(prototype, default)

        if embeb and not isinstance(prototype, Packet):
            raise ValueError("The prototype must be a Packet if you want to embeb it.")

        self.prototype = prototype
        self.embeb = embeb

    def _lets_find_a_nice_default(self, prototype, default):
        if callable(prototype) or isinstance(prototype, (UnaryExpr, BinaryExpr,
                                                         NaryExpr)):
            if default is None:
                raise ValueError("If your are using an expression of fields or a callable as the prototype of Ref I need a default object.")

            self.default = default

        elif isinstance(prototype, Packet):
            if default is not None:
                raise ValueError("We don't need a default object, we will be using the prototype object instead.")

            self.default = copy.deepcopy(prototype)

        else:
            assert False

    def _describe_yourself(self, field_name, bisturi_conf):
        desc = Field._describe_yourself(self, field_name, bisturi_conf)
        if self.embeb:
            desc.extend([(fname, f) for fname, f, _, _ in self.prototype.get_fields()])

        return desc

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)

        self.position = position

        prototype = self.prototype
        if isinstance(prototype, Packet):
            self.unpack = self._unpack_referencing_a_packet
            self.pack   = self._pack_referencing_a_packet
            self.prototype   = prototype.as_prototype()
            self.proto_class = prototype.__class__

        else:
            assert callable(prototype) or isinstance(prototype, (UnaryExpr,
                                                                 BinaryExpr,
                                                                 NaryExpr))
            from bisturi.structural_fields import normalize_raw_condition_into_a_callable
            self.prototype = normalize_raw_condition_into_a_callable(prototype)
            prototype = self.prototype

            if isinstance(self.default, Prototype):
                self.default = self.default.as_prototype()

            self.unpack = self._unpack_using_callable
            self.pack   = self._pack_with_callable

        if self.embeb:
            assert isinstance(prototype, Packet)
            self.pack   = self.pack_noop
            self.unpack = self.unpack_noop

        assert not isinstance(self.prototype, Packet)
        assert isinstance(self.prototype, Prototype) or callable(self.prototype)
        return slots

    def init(self, packet, defaults):
        # we use our prototype to get a valid default if the prototype is not a
        # callable in the other case, we use self.default.
        prototype = self.prototype
        if isinstance(prototype, Prototype):
            if self.field_name not in defaults:
                defaults[self.field_name] = prototype.clone()

            Field.init(self, packet, defaults)

        else:
            assert callable(self.prototype)
            default = self.default
            if isinstance(default, Prototype):
                if self.field_name not in defaults:
                    defaults[self.field_name] = default.clone()

            Field.init(self, packet, defaults)

    def _unpack_using_callable(self, pkt, raw, offset=0, **k):
        referenced = self.prototype(pkt=pkt, raw=raw, offset=offset, **k)

        if isinstance(referenced, Field):
            referenced.field_name=self.field_name
            referenced._compile(position=self.position, fields=[], bisturi_conf={})
            referenced.init(pkt, {})

            return referenced.unpack(pkt=pkt, raw=raw, offset=offset, **k)

        assert isinstance(referenced, Packet)

        setattr(pkt, self.field_name, referenced)
        return referenced.unpack_impl(raw, offset, **k)

    def _pack_with_callable(self, pkt, fragments, **k):
        # this can be a Packet or can be anything (but not a Field: it could be
        # a 'int' for example but not a 'Int')
        obj = getattr(pkt, self.field_name)
        if isinstance(obj, Packet):
            return obj.pack_impl(fragments=fragments, **k)

        # we try to know how to pack this value
        assert callable(self.prototype)
        # TODO add more parameters, like raw=partial_raw
        referenced = self.prototype(pkt=pkt, fragments=fragments, packing=True, **k)

        if isinstance(referenced, Field):
            referenced.field_name = self.field_name
            referenced._compile(position=self.position, fields=[], bisturi_conf={})
            #referenced.init(pkt, {})

            return referenced.pack(pkt, fragments, **k)

        # well, we are in a dead end: the 'obj' object IS NOT a Packet,
        # it is a "primitive" value however, the 'referenced' object IS
        # a Packet and we cannot do anything else
        raise NotImplementedError("I have a value to pack of type '%s' and because it is not a Packet instance I don't know how to pack it. The prototype of this Ref field is a callable so I called it hoping to receive a Field instance to show me how to pack the value but instead I received a '%s' so I'm stuck." % (type(obj), type(referenced)))


    def _unpack_referencing_a_packet(self, pkt, **k):
        p = self.proto_class(_initialize_fields=False)
        setattr(pkt, self.field_name, p)
        return p.unpack_impl(**k)

    def _pack_referencing_a_packet(self, pkt, fragments, **k):
        return getattr(pkt, self.field_name).pack_impl(fragments=fragments, **k)


@defer_operations(allowed_categories=['integer'])
class Bits(Field):
    class ByteBoundaryError(Exception):
        def __init__(self, str):
            Exception.__init__(self, str)

    def __init__(self, bit_count, default=0):
        Field.__init__(self)
        self.default = default
        self.mask = (2**bit_count)-1
        self.bit_count = bit_count

        self.iam_first = self.iam_last = False

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)

        if position == 0 or not isinstance(fields[position-1][1], Bits):
            self.iam_first = True

        if position == len(fields)-1 or not isinstance(fields[position+1][1], Bits):
            self.iam_last = True

        if self.iam_last:
            cumshift = 0
            I = Int()
            self.members = []
            for n, f in reversed(fields[:position+1]):
                if not isinstance(f, Bits):
                    break

                f.shift = cumshift
                f.mask = ((2**f.bit_count) - 1) << f.shift
                f.I = I

                self.members.append((n, f.bit_count))

                cumshift += f.bit_count
                del f.bit_count

            self.members.reverse()
            name_of_members, bit_sequence = zip(*self.members)

            if not (cumshift % 8 == 0):
                raise Bits.ByteBoundaryError("Wrong sequence of bits: %s with total sum of %i (not a multiple of 8)." % (str(list(bit_sequence)), cumshift))

            I.byte_count = cumshift // 8
            fname = "_bits__"+"_".join(name_of_members)
            I.field_name = fname
            I._compile(position=-1, fields=[], bisturi_conf={})

            slots.append(fname)
        return slots


    def init(self, packet, defaults):
        if self.iam_first:
            setattr(packet, self.I.field_name, 0)

        setattr(packet, self.field_name, defaults.get(self.field_name, self.default))

    def unpack(self, pkt, raw, offset=0, **k):
        if self.iam_first:
            offset = self.I.unpack(pkt, raw, offset, **k)

        I = getattr(pkt, self.I.field_name)

        setattr(pkt, self.field_name, (I & self.mask) >> self.shift)
        return offset

    def pack(self, pkt, fragments, **k):
        I = getattr(pkt, self.I.field_name)
        setattr(pkt, self.I.field_name, ((getattr(pkt, self.field_name) << self.shift) & self.mask) | (I & (~self.mask)))

        if self.iam_last:
            return self.I.pack(pkt, fragments=fragments, **k)
        else:
            return fragments

    def pack_regexp(self, pkt, fragments, **k):
        if self.iam_last:
            bits = []
            for name, bit_count in self.members:
                is_literal = not isinstance(getattr(pkt, name), Any)

                if is_literal:
                    b = bin(getattr(pkt, name))[2:]
                    zeros = bit_count-len(b)

                    bits.append("0" * zeros)
                    bits.append(b)
                else:
                    bits.append("x" * bit_count)

            bits  = "".join(bits)
            bytes_ = [bits[0+(i*8):8+(i*8)] for i in range(len(bits)//8)]

            for byte in bytes_:
                if byte == "x" * 8:
                    # xxxx xxxx pattern (all dont care)
                    fragments.append(b".{1}", is_literal=False)
                else:
                    first_dont_care = byte.find("x")
                    if first_dont_care == -1:
                        # 0000 0000 pattern (all fixed)
                        char = from_int_to_byte(int(byte, 2))
                        fragments.append(char, is_literal=True)

                    elif byte[first_dont_care:] == "x" * len(byte[first_dont_care:]):
                        # 00xx xxxx pattern (lower dont care)
                        dont_care_bits = len(byte[first_dont_care:])

                        lower_bin = byte[:first_dont_care] + ("0"*dont_care_bits)
                        higher_bin = byte[:first_dont_care] + ("1"*dont_care_bits)
                        lower_char = from_int_to_byte(int(lower_bin,  2))
                        higher_char = from_int_to_byte(int(higher_bin, 2))

                        lower_literal = re.escape(lower_char)
                        higher_literal = re.escape(higher_char)

                        # [lower-higher]
                        fragments.append(b'[' + \
                                          lower_literal + \
                                          b'-' + \
                                          higher_literal + \
                                          b']', is_literal=False)

                    else:
                        # 00xx x0x0 pattern (mixed pattern)
                        all_patterns   = range(256)
                        fixed_pattern  = int(byte.replace("x", "0"), 2)
                        dont_care_mask = int(byte.replace("1", "0").replace("x", "1"), 2)

                        mixed_patterns = sorted(
                                            set((p & dont_care_mask) | \
                                            fixed_pattern for p in all_patterns))

                        # [ABCD....]
                        literal_patterns = (re.escape(from_int_to_byte(p)) \
                                                        for p in mixed_patterns)
                        fragments.append(b'[' + \
                                         b''.join(literal_patterns) + \
                                         b']', is_literal=False)

        return fragments


class Bkpt(Field):
    def __init__(self):
        Field.__init__(self)

    def init(self, packet, defaults):
        pass

    def unpack(self, pkt, raw, offset=0, **k):
        import pdb
        pdb.set_trace()
        return offset

    def pack(self, pkt, fragments, **k):
        import pdb
        pdb.set_trace()
        return fragments

    def pack_regexp(self, pkt, fragments, **k):
        return fragments

class Em(Field):
    def __init__(self):
        Field.__init__(self)

    def init(self, packet, defaults):
        pass

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        return []

    def unpack(self, pkt, raw, offset=0, **k):
        return offset

    def pack(self, pkt, fragments, **k):
        fragments.append(b"")
        return fragments

