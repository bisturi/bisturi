from bisturi.field import Field, exec_once
from deferred import UnaryExpr, BinaryExpr, NaryExpr, compile_expr_into_callable, defer_operations

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
        raise ValueError("The 'when' or 'until' condition must be a callable, a field or an expression of fields but is '%s'" % (repr(raw_condition)))



def convert_a_field_raw_condition_into_a_boolean_unary_expression(a_field):
    assert isinstance(a_field, Field)

    truth_methods = ('__nonzero__', '__len__') # the order is important here, ask first for nonzero only then for len.
                                               # otherwise if 'a_field' is an Optional field and the Optional field's value
                                               # resolves to None, None doesn't have a __len__ method.
                                               # Of course, None doesn't have a __nonzero__ methods neither but 
                                               # we use 'operator.truth' as the implementation of __nonzero__
                                               # and operator.truth(None) is well defined.
    for method in truth_methods:
        if hasattr(a_field, method):
            return getattr(a_field, method)()

    raise Exception("The field instance '%s' cannot be converted to a boolean value (it isn't an int nor a iterable)" % repr(a_field))


def normalize_count_condition_into_a_callable(count_raw_condition):
    if callable(count_raw_condition):
        return count_raw_condition

    if isinstance(count_raw_condition, (int, long)):
        return lambda **k: count_raw_condition

    if isinstance(count_raw_condition, Field):
        field_name = count_raw_condition.field_name
        count_raw_condition = lambda pkt, **k: getattr(pkt, field_name)     # aka int(count_raw_condition)
  
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
                subregexp = ".*"
    
            # TODO, fix this (fix the self.get_how_many_elements stuff)
            fragments.append("(%s)*" % subregexp, is_literal=False)
            raise NotImplementedError() 
            if self.get_how_many_elements is None:
                fragments.append("(%s)*" % subregexp, is_literal=False)
            else:
                fragments.append("(%s){%i}" % (subregexp, self.get_how_many_elements), is_literal=False)

        return fragments