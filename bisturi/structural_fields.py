from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from bisturi.field import Field, exec_once
from bisturi.deferred import UnaryExpr, BinaryExpr, NaryExpr, compile_expr_into_callable, defer_operations

from bisturi.six import integer_types

def normalize_raw_condition_into_a_callable(raw_condition):
    if callable(raw_condition):
        return raw_condition

    if isinstance(raw_condition, Field):
        raw_condition = convert_a_field_raw_condition_into_a_boolean_unary_expression(raw_condition)

    if isinstance(raw_condition, (UnaryExpr, BinaryExpr, NaryExpr)):
        raw_condition = compile_expr_into_callable(raw_condition)

    if callable(raw_condition):
        return raw_condition

    else:
        raise ValueError("The argument condition must be a callable, a field or an expression of fields but is '%s'" % (repr(raw_condition)))



def convert_a_field_raw_condition_into_a_boolean_unary_expression(a_field):
    assert isinstance(a_field, Field)

    # the order is important here, ask first for nonzero only then for len.
    # otherwise if 'a_field' is an Optional field and the Optional field's value
    # resolves to None, None doesn't have a __len__ method.
    # Of course, None doesn't have a __nonzero__ methods neither but
    # we use 'operator.truth' as the implementation of __nonzero__
    # and operator.truth(None) is well defined.
    truth_methods = ('__nonzero__', '__len__')

    for method in truth_methods:
        if hasattr(a_field, method):
            return getattr(a_field, method)()

    raise Exception("The field instance '%s' cannot be converted to a boolean value (it isn't an int nor a iterable)" % repr(a_field))


def normalize_count_condition_into_a_callable(count_raw_condition):
    if callable(count_raw_condition):
        return count_raw_condition

    if isinstance(count_raw_condition, integer_types):
        return lambda **k: count_raw_condition

    if isinstance(count_raw_condition, Field):
        field_name = count_raw_condition.field_name

        # aka int(count_raw_condition)
        count_raw_condition = lambda pkt, **k: getattr(pkt, field_name)

    if isinstance(count_raw_condition, (UnaryExpr, BinaryExpr, NaryExpr)):
        count_raw_condition = compile_expr_into_callable(count_raw_condition)

    if callable(count_raw_condition):
        return count_raw_condition

    else:
        raise ValueError("The 'count' condition must be a callable, a field or an expression of fields but is '%s'" % (repr(count_raw_condition)))


@defer_operations(allowed_categories=['sequence'])
class Sequence(Field):
    ''' Sequence of a fields (aka list of field).
        See the documentation of the method Field.repeated.
        '''
    def __init__(self, prototype, count=None, until=None, when=None, default=None, aligned=None):
        Field.__init__(self)
        assert isinstance(prototype, Field)

        if (count is None and until is None) or (count is not None and until is not None):
            raise ValueError("A sequence of fields (see the Field.repeated method) must have a count "
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
        from bisturi.structural_fields import normalize_raw_condition_into_a_callable, \
                                      normalize_count_condition_into_a_callable

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
                subregexp = b".*"

            # TODO, fix this (fix the self.get_how_many_elements stuff)
            # (A)*
            fragments.append(b'(' + subregexp + b')*', is_literal=False)
            raise NotImplementedError("Not supported yet")
            if self.get_how_many_elements is None:
                fragments.append(b'(' + subregexp + b')*', is_literal=False)
            else:
                fragments.append(b'(' + subregexp + ("){%i}" % self.get_how_many_elements).encode('ascii'), is_literal=False)

        return fragments

    def repeated(self, *args, **kargs):
        r''' Nop, you cannot repeat a sequence (repeat twice):

             >>> from bisturi.packet import Packet
             >>> from bisturi.field  import Int, Data, Ref

             >>> class Buggy(Packet):                    # doctest: +ELLIPSIS
             ...    i = Int(1).repeated(2).repeated(4)
             Traceback (most recent call last):
             ...
             SyntaxError: You cannot repeat a sequence (more than one 'repeated' call is not allowed)...

             If you need this kind of 'list of list' behaviour you can do this:

             >>> class ListOfInts(Packet):
             ...    i = Int(1).repeated(2)

             >>> class NonBuggy(Packet):
             ...    i = Ref(ListOfInts).repeated(4)

             >>> raw = b'ABCDEFGH'
             >>> pkt = NonBuggy.unpack(raw)

             >>> [l_ints.i for l_ints in pkt.i]
             [[65, 66], [67, 68], [69, 70], [71, 72]]

             >>> pkt.pack() == raw
             True

             '''
        raise SyntaxError("You cannot repeat a sequence (more than one 'repeated' call is not allowed): something like Int(1).repeated(...).repeated(...). "
                          "See the documentation of Sequence.repeated for more info.")

    def when(self, *args, **kargs):
        r''' You cannot call 'when' of Sequence. Instead you can use the 'when'
             parameter of the Field.repeated method:

             >>> from bisturi.packet import Packet
             >>> from bisturi.field  import Int, Data, Ref

             >>> class Buggy(Packet):                    # doctest: +ELLIPSIS
             ...    t = Int(1)
             ...    i = Int(1).repeated(2).when(t)
             Traceback (most recent call last):
             ...
             SyntaxError: You cannot call 'when' of Sequence...

             Instead you should do something like:

             >>> class NonBuggy(Packet):
             ...    t = Int(1)
             ...    i = Int(1).repeated(2, when=t)

             '''
        raise SyntaxError("You cannot call 'when' of Sequence: something like Int(1).repeated(...).when(...). "
                          "Instead you need to use the 'when' parameter of 'repeated': Int(1).repeated(..., when=...).")


@defer_operations(allowed_categories='all') # we need all because the underlying object (value) can be an integer as well as a sequence 
class Optional(Field):
    ''' An optional field (aka the field or None).
        See the documentation of the method Field.when.
        '''
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

            obj = getattr(pkt, opt_elem_field_name)

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
                subregexp = b".*"

            # (A)?
            fragments.append(b'(' + subregexp + b')?', is_literal=False)

        return fragments

    def repeated(self, *args, **kargs):
        r''' Nop, you cannot repeat an optional argument:

             >>> from bisturi.packet import Packet
             >>> from bisturi.field  import Int, Data, Ref

             >>> class Buggy(Packet):                    # doctest: +ELLIPSIS
             ...    t = Int(1)
             ...    i = Int(1).when(t == 0).repeated(4)
             Traceback (most recent call last):
             ...
             SyntaxError: You cannot repeat an optional argument...

             Instead you should do something like:

             >>> class NonBuggy(Packet):
             ...    t = Int(1)
             ...    i = Int(1).repeated(4, when = t == 0 )

             '''
        raise SyntaxError("You cannot repeat an optional argument: something like Int(1).when(...).repeated(...). "
                          "Instead you can pass the when condition to the 'repeated' method like Int(1).repeated(..., when=...). "
                          "See the arguments of Field.repeated for more info.")

    def when(self, *args, **kargs):
        r''' This is an optional field already, you cannot chain 'when' conditions:

             >>> from bisturi.packet import Packet
             >>> from bisturi.field  import Int, Data, Ref

             >>> class Buggy(Packet):                    # doctest: +ELLIPSIS
             ...    t = Int(1)
             ...    i = Int(1).when(t > 0).when(t < 10)
             Traceback (most recent call last):
             ...
             SyntaxError: You cannot make optional an already optional field...

             Instead you should do something like:

             >>> class NonBuggy(Packet):
             ...    t = Int(1)
             ...    i = Int(1).when((t > 0) & (t < 10))

             '''
        raise SyntaxError("You cannot make optional an already optional field: something like Int(1).when(...).when(...). "
                          "Instead you need to find a single condition that represent those two conditions into a single 'when' call.")

class Move(Field):
    def __init__(self, move_arg, movement_type):
        Field.__init__(self)
        self.move_arg = move_arg
        self.movement_type = movement_type
        self.default = b''

    def unpack(self, pkt, raw, offset=0, **k):
        if isinstance(self.move_arg, Field):
            move_value = getattr(pkt, self.move_arg.field_name)

        elif isinstance(self.move_arg, integer_types):
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

        elif isinstance(self.move_arg, integer_types):
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

