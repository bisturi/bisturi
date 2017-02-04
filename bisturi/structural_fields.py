
def normalize_when_condition_into_a_callable(when_raw_condition):
    from field import Field
    from deferred import UnaryExpr, BinaryExpr, NaryExpr, compile_expr_into_callable

    if callable(when_raw_condition):
        return when_raw_condition

    if isinstance(when_raw_condition, Field):
        when_raw_condition = convert_a_field_when_condition_into_a_boolean_unary_expression(when_raw_condition)
  
    if isinstance(when_raw_condition, (UnaryExpr, BinaryExpr, NaryExpr)):
        when_raw_condition = compile_expr_into_callable(when_raw_condition)

    
    if callable(when_raw_condition):
        return when_raw_condition

    else:
        raise ValueError("The 'when' condition must be a callable, a field or an expression of fields but is '%s'" % (repr(when_raw_condition)))



def convert_a_field_when_condition_into_a_boolean_unary_expression(a_field):
    from field import Field
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
    from field import Field
    from deferred import UnaryExpr, BinaryExpr, NaryExpr, compile_expr_into_callable

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

