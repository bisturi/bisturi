import collections, functools, operator

def if_true_then_else(condition, *possible_values):
    value_if_true, value_if_false = possible_values
    return value_if_true if bool(condition) else value_if_false

def choose(index, *options):
    return options[index]

AllCategories = ['integer', 'sequence']
BinaryOperationsByCategory = {
        'integer': [
            # arith ------------------------------------
            operator.add,         operator.sub,
            operator.mul,         operator.div,
            operator.truediv,     operator.floordiv,
            operator.mod,         operator.pow,

            # cmp --------------------------------------
            operator.le,          operator.lt,
            operator.ge,          operator.gt,

            # eq ---------------------------------------
            operator.eq,          operator.ne,

            # logical ----------------------------------
            operator.and_,        operator.or_,
            operator.xor,              
            operator.rshift,      operator.lshift,
            ],

        'sequence': [
            # eq ---------------------------------------
            operator.eq,          operator.ne,

            # indexing ---------------------------------
            operator.getitem,
            ],
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


NaryExpr = collections.namedtuple('NaryExpr', ['l', 's', 'm', 'op'])
BinaryExpr = collections.namedtuple('BinaryExpr', ['l', 'r', 'op'])
UnaryExpr = collections.namedtuple('UnaryExpr', ['r', 'op'])

def compile_expr(root_expr, ops=None, ident=" "):
    from field import Field

    if ops is None:
        ops = []

    if not isinstance(root_expr, (UnaryExpr, BinaryExpr, NaryExpr, Field)):
        ops.append((0, lambda pkt, *vargs, **kargs: root_expr))
    
    elif isinstance(root_expr, NaryExpr):
        r, l, m, op = root_expr

        # XXX for one sec imagine that the t (tail) argument is a list/dict with two items
        left, right = l
        compile_expr(r, ops, ident=ident*2)
        compile_expr(left, ops, ident=ident*2)
        compile_expr(right, ops, ident=ident*2)
        ops.append((3,op))
   
    elif isinstance(root_expr, BinaryExpr):
        l, r, op = root_expr
        compile_expr(l, ops, ident=ident*2)
        compile_expr(r, ops, ident=ident*2)
        ops.append((2,op))

    elif isinstance(root_expr, UnaryExpr):
        r, op = root_expr
        compile_expr(r, ops, ident=ident*2)
        ops.append((1,op))

    else:
        field_name = root_expr.field_name
        ops.append((0, lambda pkt, *vargs, **kargs: getattr(pkt, field_name)))

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
    ops = compile_expr(root_expr)
    args = []
    return lambda pkt, *vargs, **kargs: exec_compiled_expr(pkt, args, ops, *vargs, **kargs)
   

def _defer_method(target, methodname, op, is_binary, is_nary=False):
    if is_binary:
        setattr(target, methodname, lambda A, B: BinaryExpr(A, B, op))
    else:
        if is_nary:
            setattr(target, methodname, lambda A, *B, **C: NaryExpr(A, B, C, op))
        else:
            setattr(target, methodname, lambda A: UnaryExpr(A, op))
   

def _defer_operations_of(cls, allowed_categories='all'):
    if allowed_categories == 'all':
        allowed_categories = AllCategories

    else:
        allowed_categories = list(set(allowed_categories)) # remove duplicates
        assert all((category in AllCategories) for category in allowed_categories) # sanity check

    allowed_binary_operations = sum((BinaryOperationsByCategory[category] for category in allowed_categories), [])
    allowed_unary_operations  = sum((UnaryOperationsByCategory[category]  for category in allowed_categories), [])

    for binary_op in allowed_binary_operations:
        op_name = binary_op.__name__
        if op_name.endswith("_"):
            op_name = op_name[:-1]

        methodname = "__%s__" % op_name
        _defer_method(cls, methodname, binary_op, is_binary=True)
   
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

    _defer_method(cls, 'if_true_then_else', if_true_then_else, is_binary=False, is_nary=True)
    _defer_method(cls, 'choose', choose, is_binary=False, is_nary=True)
   
    return cls

def defer_operations(allowed_categories='all'):
    def decorator(cls):
        return _defer_operations_of(cls, allowed_categories)

    return decorator

UnaryExpr = defer_operations()(UnaryExpr)
BinaryExpr = defer_operations()(BinaryExpr)
NaryExpr = defer_operations()(NaryExpr)

