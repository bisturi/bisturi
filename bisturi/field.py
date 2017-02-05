import time, struct, sys, copy, re
from packet import Packet, Prototype
from structural_fields import normalize_raw_condition_into_a_callable, \
                              normalize_count_condition_into_a_callable
from deferred import defer_operations, UnaryExpr, BinaryExpr, NaryExpr, compile_expr_into_callable
from pattern_matching import Any
from fragments import FragmentsOfRegexps

def exec_once(m):
    ''' Force to execute the method m only once and save its result.
        The next calls will always return the same result, ignoring the parameters. '''
    def wrapper(self, *args, **kargs):
        try:
            return getattr(self, "_%s_cached_result" % m.__name__)
        except AttributeError as e:
            r = m(self, *args, **kargs)
            setattr(self, "_%s_cached_result" % m.__name__, r)
            return r

    return wrapper

class Field(object):
    ''' A field represent a single parsing unit. This is the superclass from where all the other field must inherit.
        
        A field will hold a raw configuration from it initialization (__init__) until the compilation of it (_compile method).
        Once you call _compile, the field will define the most optimum version for its pack and unpack methods.
        
        See the Packet class to get a more broad view about this.
        
        Any field instance will support the following public methods besides the pack/unpack:
            - repeated: to define a sequence of fields like Int(1).repeated(4) (see the Sequence field).
            - times: an alias for repeated.
            - when: to define a field as optional like Int(1).when(foo == True) (see the Optional field).
            - at: to define where the field should start to pack/unpack (see the Move field).
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
            Each tuple contains the name of the field and the value of the field.

            The most simple case is a description that consists in a list of one tuple
                [(my name, myself)]
            but it is possible that a field requires more than one tuple to describe.
            For example, Int(1).at(x) requires two tuples one about the movement (at) and
            the other about the int itself like:
                [(my move's name, Move(x)), (my name, myself)]
            '''
        self.field_name = field_name
        if self.move_arg is None and 'align' in bisturi_conf:
            self.aligned(to=bisturi_conf['align'])

        if self.descriptor:
            self.descriptor_name = field_name

            # The original field name will be used by the descriptor. We (field) use
            # a hidden field name instead
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
        ''' Realize all the optimizations available and return a list of names which will be the
            __slots__ of the packet class. This is the time to realize all the optimizations in
            terms of speed and memory as you can. '''
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

        setattr(packet, self.field_name, obj) # if isinstance(self.default, (int, long, basestring)) else (copy.deepcopy(self.default))))

    def unpack(self, pkt, raw, offset, **k):
        raise NotImplementedError()

    def pack(self, pkt, fragments, **k):
        raise NotImplementedError()

    def unpack_noop(self, pkt, raw, offset, **k):
        ''' No-operation unpack function. Do nothing during the unpacking stage. '''
        return offset

    def pack_noop(self, pkt, fragments, **k):
        ''' No-operation pack function. Do nothing during the packing stage. '''
        return fragments

    def repeated(self, count=None, until=None, when=None, default=None, aligned=None):
        ''' Describe a sequence of fields instead of a single field. Repeat this field
            'count' times or 'until' the given condition is false. '''
        assert not (count is None and until is None)
        assert not (count is not None and until is not None)

        return Sequence(prototype=self, count=count, until=until, when=when, default=default, aligned=aligned)

    def when(self, condition, default=None):
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

Field.times = Field.repeated


@defer_operations(allowed_categories=['sequence'])
class Sequence(Field):
    def __init__(self, prototype, count=None, until=None, when=None, default=None, aligned=None):
        Field.__init__(self)
        assert isinstance(prototype, Field)

        if (count is None and until is None) or (count is not None and until is not None):
            raise ValueError("A sequence of fields (repeated or times) must have or a count "
                             "of how many a field is repeated or a until condition to repeat "
                             "the field as long as the condition is false. "
                             "You must set one and only one of them.") 

        self.ctime = prototype.ctime
        self.default = default if default is not None else []

        self.prototype_field = prototype
        self.aligned_to = aligned

        self.tmp = (count, until, when)

      
    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)
        if self.aligned_to is None:
            self.aligned_to = bisturi_conf.get('align', 1)

        # XXX we are propagating the 'align' attribute (in bisturi_conf) to
        # the prototype packet. This is valid ...but inelegant
        # This happen in others fields like Optional and Ref
        self.seq_elem_field_name = "_seq_elem__"+self.field_name
        self.prototype_field.field_name = self.seq_elem_field_name
        self.prototype_field._compile(position=-1, fields=[], bisturi_conf=bisturi_conf)

        count, until, when = self.tmp
      
        self.when = None if when is None else normalize_raw_condition_into_a_callable(when)

        if count is None:
            self.get_how_many_elements  = None
            self.until_condition = normalize_raw_condition_into_a_callable(until)
        else:
            self.get_how_many_elements  = normalize_count_condition_into_a_callable(count)
            self.until_condition = None

        return slots + [self.seq_elem_field_name]

    def init(self, packet, defaults):
        Field.init(self, packet, defaults)
        self.prototype_field.init(packet, {})
    
    def unpack(self, pkt, raw, offset=0, **k):
        sequence = [] 
        setattr(pkt, self.field_name, sequence) # clean up the previous sequence (if any), 
                                                # so it can be used by the 'when' or 'until' callbacks

        count_elements = 1 if not self.get_how_many_elements else \
                           self.get_how_many_elements(pkt=pkt, raw=raw, offset=offset, **k)

        when = self.when
        if when and (count_elements <= 0 or not when(pkt=pkt, raw=raw, offset=offset, **k)):
            return offset

        seq_elem_field_name = self.seq_elem_field_name
        unpack = self.prototype_field.unpack
        append = sequence.append
        aligned_to = self.aligned_to
        for _ in range(count_elements):
            offset += (aligned_to - (offset % aligned_to)) % aligned_to
            offset =  unpack(pkt=pkt, raw=raw, offset=offset, **k)

            # because the unpack method must return a new instance or object each
            # time that it is called, we know that all the objects returned will be
            # different so we can append each one without worrying to be appending
            # several times the same object (and for that we don't need to create
            # a copy or anything else)
            append(getattr(pkt, seq_elem_field_name))

        until = self.until_condition
        should_continue = False if until is None else not until(pkt=pkt, raw=raw, offset=offset, **k)
        while should_continue:
            offset += (aligned_to - (offset % aligned_to)) % aligned_to
            offset =  unpack(pkt=pkt, raw=raw, offset=offset, **k)

            append(getattr(pkt, seq_elem_field_name))
            should_continue = not until(pkt=pkt, raw=raw, offset=offset, **k)

        return offset


    def pack(self, pkt, fragments, **k):
        sequence = getattr(pkt, self.field_name)
        seq_elem_field_name = self.seq_elem_field_name
        aligned_to = self.aligned_to
        pack = self.prototype_field.pack
        for val in sequence:
            setattr(pkt,  seq_elem_field_name, val)
            fragments.current_offset += (aligned_to - (fragments.current_offset % aligned_to)) % aligned_to
            pack(pkt, fragments, **k)

        return fragments

    def pack_regexp(self, pkt, fragments, **k):
        value = getattr(pkt, self.field_name)
        is_literal = not isinstance(value, Any)

        if is_literal:
            self.pack(pkt, fragments, **k)
        else:
            f = FragmentsOfRegexps()
            try:
                self.prototype_field.pack_regexp(pkt, f, **k)
                subregexp = f.assemble_regexp()
            except:
                subregexp = ".*"
          
            raise NotImplementedError() # TODO, fix this (fix the self.get_how_many_elements stuff)
            if self.get_how_many_elements is None:
                fragments.append("(%s)*" % subregexp, is_literal=False)
            else:
                fragments.append("(%s){%i}" % (subregexp, self.get_how_many_elements), is_literal=False)

        return fragments

@defer_operations(allowed_categories='all') # we need all because the underlying object (value) can be an interger as well as a sequence 
class Optional(Field):
    def __init__(self, prototype, when, default=None):
        Field.__init__(self)
        assert isinstance(prototype, Field)

        self.ctime = prototype.ctime
        self.default = default

        self.prototype_field = prototype
        self.tmp = when

      
    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)
        self.opt_elem_field_name = "_opt_elem__"+self.field_name
        self.prototype_field.field_name = self.opt_elem_field_name
        self.prototype_field._compile(position=-1, fields=[], bisturi_conf=bisturi_conf)

        when = self.tmp
        del self.tmp

        self.when = normalize_raw_condition_into_a_callable(when)
        return slots + [self.opt_elem_field_name]

    def init(self, packet, defaults):
        Field.init(self, packet, defaults)
        self.prototype_field.init(packet, {})
      
    def unpack(self, pkt, raw, offset=0, **k):
        proceed = self.when(pkt=pkt, raw=raw, offset=offset, **k)

        opt_elem_field_name = self.opt_elem_field_name
        obj = None
        if proceed:
            offset = self.prototype_field.unpack(pkt=pkt, raw=raw, offset=offset, **k)

            obj = getattr(pkt, opt_elem_field_name) # if this is a Packet instance, obj is the same object each iteration, so we need a copy

        setattr(pkt, self.field_name, obj)
        return offset


    def pack(self, pkt, fragments, **k):
        obj = getattr(pkt, self.field_name)
        opt_elem_field_name = self.opt_elem_field_name
        if obj is not None:
            setattr(pkt,  opt_elem_field_name, obj)
            return self.prototype_field.pack(pkt, fragments, **k)

        else:
            return fragments
   
    def pack_regexp(self, pkt, fragments, **k):
        value = getattr(pkt, self.field_name)
        is_literal = not isinstance(value, Any)

        if is_literal:
            self.pack(pkt, fragments, **k)
        else:
            f = FragmentsOfRegexps()
            try:
                self.prototype_field.pack_regexp(pkt, f, **k)
                subregexp = f.assemble_regexp()
            except:
                subregexp = ".*"
          
            fragments.append("(%s)?" % subregexp, is_literal=False)

        return fragments


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
            self.endianness = bisturi_conf.get('endianness', 'big') # try to get the default from the Packet class; big endian by default

        self.is_bigendian = (self.endianness in ('big', 'network')) or (self.endianness == 'local' and sys.byteorder == 'big')
      
        if self.byte_count in (1, 2, 4, 8): 
            code = {1:'B', 2:'H', 4:'I', 8:'Q'}[self.byte_count]
            if self.is_signed:
                code = code.lower()

            self.struct_code = code
            fmt = (">" if self.is_bigendian else "<") + code
            self.struct_obj = struct.Struct(fmt)

            self.pack, self.unpack = self._pack_fixed_and_primitive_size, self._unpack_fixed_and_primitive_size

        else:
            self.struct_code = None
            self.base = 2**(self.byte_count*8) 
            self.xcode = ("%0" + str(self.byte_count*2) + "x")

            self.pack, self.unpack = self._pack_fixed_size, self._unpack_fixed_size

        return slots
   
    def init(self, packet, defaults):
        setattr(packet, self.field_name, defaults.get(self.field_name, self.default))
 
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
        if not self.is_bigendian:
            raw_data = raw_data[::-1]
      
        num = int(raw_data.encode('hex'), 16)
        if self.is_signed and ord(raw_data[0]) > 127:
            num = -(self.base - num)

        setattr(pkt, self.field_name, num)
        return next_offset

    def _pack_fixed_size(self, pkt, fragments, **k):
        integer = getattr(pkt, self.field_name)
        num = (self.base + integer) if integer < 0 else integer

        data = (self.xcode % num).decode('hex')
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
            fragments.append(".{%i}" % self.byte_count, is_literal=False)

        return fragments

@defer_operations(allowed_categories=['sequence'])
class Data(Field):
    def __init__(self, byte_count=None, until_marker=None, include_delimiter=False, consume_delimiter=True, default=''):
        Field.__init__(self)
        assert (byte_count is None and until_marker is not None) or (until_marker is None and byte_count is not None)

        self.default = default
        if not default and isinstance(byte_count, (int, long)):
            self.default = "\x00" * byte_count
      
        self.byte_count = byte_count 
        self.until_marker = until_marker

        self.include_delimiter = include_delimiter
        self.delimiter_to_be_included = self.until_marker if isinstance(self.until_marker, basestring) and not include_delimiter else ''

        assert not (consume_delimiter == False and include_delimiter == True)
        self.consume_delimiter = consume_delimiter #XXX document this!
        self.is_fixed = isinstance(byte_count, (int, long))

    @exec_once
    def _compile(self, position, fields, bisturi_conf):
        slots = Field._compile_impl(self, position, fields, bisturi_conf)

        if self.byte_count is not None:
            if isinstance(self.byte_count, (int, long)):
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
                assert self._search_buffer_length >= 0 # the length can be 0 or None (means infinite) or a positive number

            if isinstance(self.until_marker, basestring):
                self.unpack = self._unpack_with_string_marker

            elif hasattr(self.until_marker, 'search'):
                self.unpack = self._unpack_with_regexp_marker
         
            else:
                assert False

        return slots
   
    def init(self, packet, defaults):
        setattr(packet, self.field_name, defaults.get(self.field_name, self.default))

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
            raise Exception("Unpacked %i bytes but expected %i" % (len(chunk), byte_count))

        setattr(pkt, self.field_name, chunk)
      
        return next_offset
   
    def _unpack_variable_size_field(self, pkt, raw, offset=0, **k):
        byte_count = getattr(pkt, self.byte_count.field_name)
        next_offset = offset + byte_count
      
        chunk = raw[offset:next_offset]
        if len(chunk) != byte_count:
            raise Exception("Unpacked %i bytes but expected %i" % (len(chunk), byte_count))

        setattr(pkt, self.field_name, chunk)
      
        return next_offset
   
    def _unpack_variable_size_callable(self, pkt, raw, offset=0, **k):
        byte_count = self.byte_count(pkt=pkt, raw=raw, offset=offset, **k)
        next_offset = offset + byte_count
      
        chunk = raw[offset:next_offset]
        if len(chunk) != byte_count:
            raise Exception("Unpacked %i bytes but expected %i" % (len(chunk), byte_count))

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
        if until_marker.pattern == "$":    # shortcut
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
            custom_regexp = value.regexp.pattern if value.regexp is not None else ".*"
            if self.byte_count is not None:
                if isinstance(self.byte_count, (int, long)):
                    byte_count = self.byte_count
             
                elif isinstance(self.byte_count, Field):
                    byte_count = getattr(pkt, self.byte_count.field_name)

                elif callable(self.byte_count):
                    try:
                        byte_count = self.byte_count(pkt=pkt, **k)
                    except Exception, e:
                        byte_count = None

                if byte_count is not None:
                    fragments.append(".{%i}" % byte_count, is_literal=False) # TODO ignoring the custom regexp!!
                else:
                    fragments.append(custom_regexp, is_literal=False)

            else:
                endswith = re.escape(self.until_marker) if isinstance(self.until_marker, basestring) else self.until_marker.pattern
                fragments.append(custom_regexp + endswith, is_literal=False)
             
        return fragments

class Ref(Field):
    r''' Reference to another packet description. This field allows to composite different packet descriptions.
        
        The prototype parameter must be a packet class, a packet instance or a callable.
        If it is the latter, the callable must return a packet instance or a field instance each time
        that it is called. Because of that, the callable must to return a new packet/field instance each time, 
        you cannot return the same object twice.
        
        The callable will be called during the unpack stage but it can also be called during the pack stage to
        determinate how to pack a value when this one is not a packet instance (let's say that you are referencing
        to an Int field and I have the value 42, I need to call the callable to get an Int instance to pack the 42).
        In this case the callable will be call with the parameter packing=True.

        If the prototype is a packet, then the default it is not needed becasue we can use the prototype as
        a default value for the field.
        But if it is a callable, the default is mandatory otherwise we cannot know how to create a default value
        for the field.

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

        >>> str(pkt.pack()) == '\x01\x02\x00\x00\x00\x07'
        True

        >>> raw = '\x01\x02\x03\x04\x05\x06'
        >>> pkt = Line.unpack(raw)
        
        >>> (pkt.begin.x, pkt.begin.y)
        (1, 2)
        >>> (pkt.end.x, pkt.end.y)
        (3, 4)
        >>> (pkt.extra.x, pkt.extra.y)
        (5, 6)

        >>> str(pkt.pack()) == raw
        True


        If the embeb parameter is True, the prototype must be a packet. With this flag all the fields of the
        prototype are borrow to the current packet.
        The embeb feature is quite experimental and has a few quirks:

        >>> class Point3D(Packet):
        ...     point_2d = Ref(Point(x=1, y=2), embeb=True)
        ...     z = Int(1)

        >>> pkt = Point3D(x=7)
        >>> (pkt.x, pkt.y, pkt.z) # XXX this should be (7, 2, 0) but...
        (7, 0, 0)

        >>> pkt.x = 8
        >>> pkt.point_2d.y = 9
        >>> str(pkt.pack()) == '\x08\x00\x00' # XXX but it should be 08 09 00
        True

        >>> raw = '\x01\x02\x03'
        >>> pkt = Point3D.unpack(raw)
        >>> (pkt.x, pkt.y, pkt.z)
        (1, 2, 3)

        >>> str(pkt.pack()) == '\x01\x02\x03'
        True

        '''

    def __init__(self, prototype, default=None, embeb=False, _is_a_subpacket_definition=False):
        Field.__init__(self)

        if _is_a_subpacket_definition:
            self.ctime = prototype.get_fields()[0][1].ctime

        self.default = default

        if isinstance(prototype, type):
            prototype = prototype() # get an object, this allows write  Ref(PacketClass) instead of Ref(PacketClass())
      
        if not isinstance(prototype, Packet) and not callable(prototype):
            raise ValueError("The prototype of a Ref field must be a packet (class or instance) or a callable that should return a Field or a Packet.")

            
        self._lets_find_a_nice_default(prototype, default)

        if embeb and not isinstance(prototype, Packet):
            raise ValueError("The prototype must be a Packet if you want to embeb it.")
            
        self.prototype = prototype
        self.embeb = embeb 

    def _lets_find_a_nice_default(self, prototype, default):
        if callable(prototype):
            if default is None:
                raise ValueError("If your are using a callable as the prototype of Ref I need a default object.")

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
            assert callable(prototype)
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
        # we use our prototype to get a valid default if the prototype is not a callable
        # in the other case, we use self.default.
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
        obj = getattr(pkt, self.field_name)  # this can be a Packet or can be anything (but not a Field: it could be a 'int' for example but not a 'Int')
        if isinstance(obj, Packet):
            return obj.pack_impl(fragments=fragments, **k)

        # we try to know how to pack this value
        assert callable(self.prototype)
        referenced = self.prototype(pkt=pkt, fragments=fragments, packing=True, **k)   # TODO add more parameters, like raw=partial_raw

        if isinstance(referenced, Field):
            referenced.field_name = self.field_name
            referenced._compile(position=self.position, fields=[], bisturi_conf={})
            #referenced.init(pkt, {})

            return referenced.pack(pkt, fragments, **k)

        # well, we are in a dead end: the 'obj' object IS NOT a Packet, it is a "primitive" value
        # however, the 'referenced' object IS a Packet and we cannot do anything else
        raise NotImplementedError("I have a value to pack of type '%s' and because it is not a Packet instance "
                                  "I don't know how to pack it. The prototype of this Ref field is a callable so "
                                  "I called it hoping to receive a Field instance to show me how to pack the value "
                                  "but instead I received a '%s' so I'm stuck." % (type(obj), type(referenced)))


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

            I.byte_count = cumshift / 8
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
            bytes = [bits[0+(i*8):8+(i*8)] for i in range(len(bits)/8)]

            for byte in bytes:
                if byte == "x" * 8:                                   # xxxx xxxx pattern (all dont care)
                    fragments.append(".{1}", is_literal=False)
                else:
                    first_dont_care = byte.find("x")
                    if first_dont_care == -1:                         # 0000 0000 pattern (all fixed)
                        char = chr(int(byte, 2))
                        fragments.append(char, is_literal=True)

                    elif byte[first_dont_care:] == "x" * len(byte[first_dont_care:]):
                        dont_care_bits = len(byte[first_dont_care:])   # 00xx xxxx pattern (lower dont care)
                        lower_char = chr(int(byte[:first_dont_care] + ("0" * dont_care_bits),  2))
                        higher_char = chr(int(byte[:first_dont_care] + ("1" * dont_care_bits), 2))

                        lower_literal = re.escape(lower_char)
                        higher_literal = re.escape(higher_char)
                        fragments.append("[%s-%s]" % (lower_literal, higher_literal), is_literal=False)
                  
                    else:                                             # 00xx x0x0 pattern (mixed pattern)
                        all_patterns   = range(256)
                        fixed_pattern  = int(byte.replace("x", "0"), 2) 
                        dont_care_mask = int(byte.replace("1", "0").replace("x", "1"), 2)

                        mixed_patterns = sorted(set((p & dont_care_mask) | fixed_pattern for p in all_patterns))
                     
                        literal_patterns = (re.escape(chr(p)) for p in mixed_patterns)
                        fragments.append("[%s]" % "".join(literal_patterns), is_literal=False)

        return fragments

class Move(Field):
    def __init__(self, move_arg, movement_type):
        Field.__init__(self)
        self.move_arg = move_arg 
        self.movement_type = movement_type
        self.default = ''

    def unpack(self, pkt, raw, offset=0, **k):
        if isinstance(self.move_arg, Field):
            move_value = getattr(pkt, self.move_arg.field_name)

        elif isinstance(self.move_arg, (int, long)):
            move_value = self.move_arg
      
        else:
            assert callable(self.move_arg) # TODO the callable must have the same interface. currently recieve (pkt, raw, offset, **k) for unpack and (pkt, fragments, **k) for pack
            move_value = self.move_arg(pkt=pkt, raw=raw, offset=offset, **k)

        # TODO we need to disable this, the data may be readed by other field
        # in the future and then the packet will have duplicated data (but see pack())
        #setattr(pkt, self.field_name, raw[offset:move_value])
        if self.movement_type == 'absolute':
            return move_value
        elif self.movement_type == 'relative':
            return offset + move_value
        elif self.movement_type.startswith('align-'):
            if self.movement_type == 'align-global':
                start = 0
            elif self.movement_type == 'align-local':
                start = k['local_offset']
            else:
                raise Exception()

            return offset + ((move_value - ((offset-start) % move_value)) % move_value)
        else:     
            raise Exception()
   
    def init(self, packet, defaults):
        pass

    def pack(self, pkt, fragments, **k):
        #garbage = getattr(pkt, self.field_name)

        if isinstance(self.move_arg, Field):
            move_value = getattr(pkt, self.move_arg.field_name)
 
        elif isinstance(self.move_arg, (int, long)):
            move_value = self.move_arg
      
        else:
            assert callable(self.move_arg)
            move_value = self.move_arg(pkt=pkt, fragments=fragments, **k)
     
        # TODO because the "garbage" could be readed by another field in the future,
        # this may not be garbage and if  we try to put here, the other field will
        # try to put the same data in the same place and we get a collission.
        #fragments.append(garbage)
        if self.movement_type == 'absolute':
            fragments.current_offset = move_value
        elif self.movement_type == 'relative':
            fragments.current_offset += move_value
        elif self.movement_type.startswith('align-'):
            offset = fragments.current_offset
            if self.movement_type == 'align-global':
                start = 0
            elif self.movement_type == 'align-local':
                start = k['local_offset']
            else:
                raise Exception()

            fragments.current_offset += ((move_value - ((offset-start) % move_value)) % move_value)
        else:
            raise Exception()

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
        fragments.append("")
        return fragments

