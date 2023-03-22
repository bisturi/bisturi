import collections, functools, operator


def if_true_then_else(condition, possible_values):
    value_if_true, value_if_false = possible_values
    return value_if_true if bool(condition) else value_if_false


def chooses(index, options):
    return options[index]


AllCategories = ['integer', 'sequence']
BinaryOperationsByCategory = {
    'integer': [
        # arith ------------------------------------
        operator.add,
        operator.sub,
        operator.mul,
        operator.truediv,
        operator.floordiv,
        operator.mod,
        operator.pow,

        # cmp --------------------------------------
        operator.le,
        operator.lt,
        operator.ge,
        operator.gt,

        # eq ---------------------------------------
        operator.eq,
        operator.ne,

        # logical ----------------------------------
        operator.and_,
        operator.or_,
        operator.xor,
        operator.rshift,
        operator.lshift,
    ],
    'sequence': [
        # eq ---------------------------------------
        operator.eq,
        operator.ne,

        # indexing ---------------------------------
        operator.getitem,
    ],
}

BinaryReverseOperationsByCategory = {
    'integer': [
        # arith ------------------------------------
        operator.add,
        operator.sub,
        operator.mul,
        operator.truediv,
        operator.floordiv,
        operator.mod,
        operator.pow,

        # logical ----------------------------------
        operator.and_,
        operator.or_,
        operator.xor,
        operator.rshift,
        operator.lshift,
    ],
    'sequence': [],
}

UnaryOperationsByCategory = {
    'integer': [
        # arith ------------------------------------
        operator.neg,

        # logical ----------------------------------
        operator.inv,

        # value ------------------------------------
        operator.truth,
    ],
    'sequence': [
        # length -----------------------------------
        len,
    ],
}

# For
NaryExpr = collections.namedtuple(
    'NaryExpr', ['left', 'arglist', 'argmapping', 'op']
)

# For x + y
BinaryExpr = collections.namedtuple('BinaryExpr', ['left', 'right', 'op'])

# For -x
UnaryExpr = collections.namedtuple('UnaryExpr', ['arg', 'op'])


class Operations(object):
    def __init__(self):
        self.ops = []

    def append(self, num_arguments, operation, level, operation_name=None):
        if operation_name is None:
            operation_name = repr(operation)

        self.ops.append((num_arguments, operation, level, operation_name))

    def as_list(self):
        return [
            (num_arguments, operation)
            for num_arguments, operation, _, _ in self.ops
        ]


def compile_expr(root_expr, ops=None, level=0, verbose=False):
    from bisturi.field import Field
    next_level = level + 1

    if ops is None:
        ops = Operations()

    if not isinstance(root_expr, (UnaryExpr, BinaryExpr, NaryExpr, Field)):
        # the identity function.
        # example: 42 -> [42]
        cb = lambda pkt, *vargs, **kargs: root_expr
        ops.append(0, cb, level, 'literal-value ' + repr(root_expr))

    elif isinstance(root_expr, NaryExpr):
        # root_expr is "op(x, list)" or "op(x, mapping)",
        # compile x then each element of list/mapping and append
        # a single element representing the whole list/mapping
        # and then the op
        #
        # example: foo(x, [y, z]) -> [x, (y, z), foo]
        # example: foo(x, {k1=y, k2=z}) -> [x, {k1=y, k2=z}, foo]
        left, arglist, argmapping, op = root_expr

        compile_expr(left, ops, level=next_level)

        assert arglist or argmapping
        assert not (arglist and argmapping)

        if arglist:
            n = len(arglist)
            for value in arglist:
                compile_expr(value, ops, level=next_level)

            cb = lambda *vargs: vargs
            ops.append(n, cb, level, 'arg-list')

        else:
            n = len(argmapping)
            keys, values = zip(*argmapping.items())
            for value in values:
                compile_expr(value, ops, level=next_level)

            cb = lambda *vargs: dict(zip(keys, vargs))
            ops.append(n, cb, level, 'arg-mapping')

        ops.append(2, op, level)

    elif isinstance(root_expr, BinaryExpr):
        # root_expr is "op(x, y)", compile x and y and append then op
        # example: x + y -> [x, y, +]
        l, r, op = root_expr
        compile_expr(l, ops, level=next_level)
        compile_expr(r, ops, level=next_level)
        ops.append(2, op, level)

    elif isinstance(root_expr, UnaryExpr):
        # root_expr is "op(x)", compile x and append then op
        # example: -x  -> [x, -]
        a, op = root_expr
        compile_expr(a, ops, level=next_level)
        ops.append(1, op, level)

    elif isinstance(root_expr, Field):
        if hasattr(root_expr, 'field_name'):
            field_name = root_expr.field_name
            cb = lambda pkt, *vargs, **kargs: getattr(pkt, field_name)
            ops.append(0, cb, level, 'field-lookup ' + repr(root_expr))
        else:
            cb = lambda pkt, *vargs, **kargs: root_expr
            ops.append(0, cb, level, 'literal-field-value ' + repr(root_expr))
    else:
        raise Exception("Invalid argument of type %s" % repr(type(root_expr)))

    return ops


def exec_compiled_expr(pkt, args, ops, *vargs, **kargs):
    args = list(args)

    for arg_count, op in ops:
        if arg_count == 0:
            result = op(pkt, *vargs, **kargs)
        else:
            result = op(*reversed(args[:arg_count]))
            del args[:arg_count]

        args.insert(0, result)

    assert len(args) == 1
    return args[0]


def compile_expr_into_callable(root_expr):
    ops = compile_expr(root_expr).as_list()
    args = []
    return lambda pkt, *vargs, **kargs: exec_compiled_expr(
        pkt, args, ops, *vargs, **kargs
    )


def _defer_method(
    target,
    methodname,
    op,
    is_binary,
    is_nary=False,
    swap_binary_arguments=False
):
    ''' Creates a method definition and set it to the given target
        (possible a class).

        The definition will be save under the given methodname.

        The method, once called, it will return a:
          - UnaryExpr if is_binary == False and is_nary == False
          - BinaryExpr if is_binary == True
          - NaryExpr if is_binary == False and is_nary == True

        All of these xxExpr are representation of the given operator
        (a unary, binary or nary operator).

        The idea is that calling x + 1 *does not* do the real addition.
        Instead, x + 1 returns a BinaryExpr between x and 1 with the
        addition as its associated operation.

        In this way we can defer the operation.
    '''
    if is_binary:
        if swap_binary_arguments:
            setattr(target, methodname, lambda A, B: BinaryExpr(B, A, op))
        else:
            setattr(target, methodname, lambda A, B: BinaryExpr(A, B, op))
    else:
        if is_nary:

            def nary(A, *B, **C):
                assert B or C
                assert not (B and C)

                is_keyword_call = bool(C)

                # nary supports different ways to call it:
                #   - keyword-arguments-only: nary(k1=v1, k2=v2)
                #   - dictionary: nary({k1: v1, k2: v2})
                #   - list/tuple: nary([v1, v2])
                #   - positional-arguments-only: nary(v1, v2)
                # the following code tries to see which way was chosen
                if not C and len(B) == 1:
                    if isinstance(B[0], dict):  # nary({k1: v1, k2: v2})
                        C = B[0]
                        B = []
                    elif isinstance(B[0], (list, tuple)):  # nary([v1, v2])
                        B = B[0]
                        C = {}

                    else:
                        raise Exception(
                            "Invalid argument for nary expression '%s'. Valid arguments can be a single list or dict (like nary([a, b]) or nary({k1: a, k2: b})), a list of arguments (like nary(a, b)) or a keyword arguments call (like nary(k1=a, k2=b))."
                            % methodname
                        )

                elif C:  # nary(k1=v1, k2=v2)

                    def _encode_to_ascii_or_fail(obj):
                        if not isinstance(obj, str):
                            return obj  # as is

                        try:
                            return obj.encode('ascii')
                        except:
                            raise Exception(
                                "Invalid argument for nary expression '%s'. Your are using a keyword arguments call (like nary(k1=a, k2=b)) where the keywords aren't valid ascii names (chars between 0 and 128)."
                                % methodname
                            )

                    C = {_encode_to_ascii_or_fail(k): v for k, v in C.items()}

                # else  --> nary(v1, v2)

                # after the processing of above we should have:
                #   - A being the first argument of the nary operation
                #   - B being the next N arguments as a list
                #   - C being the next M arguments as a dictionary
                # the nary operation may operate over A and B or A and C
                # but never over A and B and C
                assert B or C
                assert not (B and C)
                return NaryExpr(A, B, C, op)

            setattr(target, methodname, nary)
        else:
            setattr(target, methodname, lambda A: UnaryExpr(A, op))


def _defer_operations_of(cls, allowed_categories='all'):
    if allowed_categories == 'all':
        allowed_categories = AllCategories

    else:
        allowed_categories = list(set(allowed_categories))  # remove duplicates
        assert all(
            (category in AllCategories) for category in allowed_categories
        )  # sanity check

    allowed_binary_operations = sum(
        (
            BinaryOperationsByCategory[category]
            for category in allowed_categories
        ), []
    )
    allowed_binary_reverse_operations = sum(
        (
            BinaryReverseOperationsByCategory[category]
            for category in allowed_categories
        ), []
    )
    allowed_unary_operations = sum(
        (
            UnaryOperationsByCategory[category]
            for category in allowed_categories
        ), []
    )

    # for each binary operation (op) create a magic
    # method named __op__ that when it gets call it will return
    # a deferred operation (unary/binary/nary deferred operation)
    # that would represent op without executing it (hence the name)
    for binary_op in allowed_binary_operations:
        op_name = binary_op.__name__
        if op_name.endswith("_"):
            op_name = op_name[:-1]

        methodname = "__%s__" % op_name
        _defer_method(cls, methodname, binary_op, is_binary=True)

    for binary_op in allowed_binary_reverse_operations:
        op_name = binary_op.__name__
        if op_name.endswith("_"):
            op_name = op_name[:-1]

        methodname = "__r%s__" % op_name
        _defer_method(
            cls,
            methodname,
            binary_op,
            is_binary=True,
            swap_binary_arguments=True
        )

    for unary_op in allowed_unary_operations:
        op_name = unary_op.__name__
        if op_name.endswith("_"):
            op_name = op_name[:-1]

        if op_name == "inv":
            op_name = "invert"
        elif op_name == "truth":
            op_name = "nonzero"

        methodname = "__%s__" % op_name
        _defer_method(cls, methodname, unary_op, is_binary=False)

    _defer_method(
        cls,
        'if_true_then_else',
        if_true_then_else,
        is_binary=False,
        is_nary=True
    )
    _defer_method(cls, 'chooses', chooses, is_binary=False, is_nary=True)

    return cls


def defer_operations(allowed_categories='all'):
    ''' Decorate the class adding it several magic methods that when
        called they will return deferred operations.

        For example x + 1 will call __add__ which it will return
        BinaryExpr(x, 1, operator.add). So instead of executing the
        addition we return an object that represents the addition.

        The object returned will be interpreted by Field to make sense
        of it and executing the real operation during the runtime
        (pack/unpack time).

        allowed_categories says which subset of the operations would be
        added to the class.
    '''
    def decorator(cls):
        return _defer_operations_of(cls, allowed_categories)

    return decorator


UnaryExpr = defer_operations()(UnaryExpr)
BinaryExpr = defer_operations()(BinaryExpr)
NaryExpr = defer_operations()(NaryExpr)
