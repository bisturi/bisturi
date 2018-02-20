from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from bisturi.six import text_types

import collections, functools, operator

def if_true_then_else(condition, possible_values):
    value_if_true, value_if_false = possible_values
    return value_if_true if bool(condition) else value_if_false

def choose(index, options):
    return options[index]

AllCategories = ['integer', 'sequence']
BinaryOperationsByCategory = {
        'integer': [
            # arith ------------------------------------
            operator.add,         operator.sub,
            operator.mul,
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

BinaryReverseOperationsByCategory = {
        'integer': [
            # arith ------------------------------------
            operator.add,         operator.sub,
            operator.mul,
            operator.truediv,     operator.floordiv,
            operator.mod,         operator.pow,

            # logical ----------------------------------
            operator.and_,        operator.or_,
            operator.xor,
            operator.rshift,      operator.lshift,
            ],

        'sequence': [
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

class Operations(object):
    def __init__(self):
        self.ops = []

    def append(self, num_arguments, operation, level, operation_name=None):
        if operation_name is None:
            operation_name = repr(operation)

        self.ops.append((num_arguments, operation, level, operation_name))

    def as_list(self):
        return [(num_arguments, operation) for num_arguments, operation, _, _ in self.ops]


def compile_expr(root_expr, ops=None, level=0, verbose=False):
    from bisturi.field import Field
    next_level = level + 1

    if ops is None:
        ops = Operations()

    if not isinstance(root_expr, (UnaryExpr, BinaryExpr, NaryExpr, Field)):
        ops.append(0, lambda pkt, *vargs, **kargs: root_expr, level, 'literal-value ' + repr(root_expr))

    elif isinstance(root_expr, NaryExpr):
        r, l, m, op = root_expr

        compile_expr(r, ops, level=next_level)

        assert l or m
        assert not (l and m)

        if l:
            n = len(l)
            for value in l:
                compile_expr(value, ops, level=next_level)

            ops.append(n, lambda *vargs: vargs, level, 'arg-list')

        else:
            n = len(m)
            keys, values = zip(*m.items())
            for value in values:
                compile_expr(value, ops, level=next_level)

            ops.append(n, lambda *vargs: dict(zip(keys, vargs)), level, 'arg-mapping')

        ops.append(2, op, level)

    elif isinstance(root_expr, BinaryExpr):
        l, r, op = root_expr
        compile_expr(l, ops, level=next_level)
        compile_expr(r, ops, level=next_level)
        ops.append(2, op, level)

    elif isinstance(root_expr, UnaryExpr):
        r, op = root_expr
        compile_expr(r, ops, level=next_level)
        ops.append(1, op, level)

    elif isinstance(root_expr, Field):
        if hasattr(root_expr, 'field_name'):
            field_name = root_expr.field_name
            ops.append(0, lambda pkt, *vargs, **kargs: getattr(pkt, field_name), level, 'field-lookup ' + repr(root_expr))
        else:
            ops.append(0, lambda pkt, *vargs, **kargs: root_expr, level, 'literal-field-value ' + repr(root_expr))
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
    return lambda pkt, *vargs, **kargs: exec_compiled_expr(pkt, args, ops, *vargs, **kargs)


def _defer_method(target, methodname, op, is_binary, is_nary=False, swap_binary_arguments=False):
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

                if not C and len(B) == 1:
                    if isinstance(B[0], dict):  # nary({k1: v1, k2: v2})
                        C = B[0]
                        B = []
                    elif isinstance(B[0], (list, tuple)):   # nary([v1, v2])
                        B = B[0]
                        C = {}

                    else:
                        raise Exception("Invalid argument for nary expression '%s'. Valid arguments can be a single list or dict (like nary([a, b]) or nary({k1: a, k2: b})), a list of arguments (like nary(a, b)) or a keyword arguments call (like nary(k1=a, k2=b))." % methodname)

                elif C:                                 # nary(k1=v1, k2=v2)
                    def _encode_to_ascii_or_fail(obj):
                        if not isinstance(obj, text_types):
                            return obj # as is

                        try:
                            return obj.encode('ascii')
                        except:
                            raise Exception("Invalid argument for nary expression '%s'. Your are using a keyword arguments call (like nary(k1=a, k2=b)) where the keywords aren't valid ascii names (chars between 0 and 128)." % methodname)

                    C = {_encode_to_ascii_or_fail(k): v for k, v in C.items()}

                # else  --> nary(v1, v2)

                return NaryExpr(A, B, C, op)

            setattr(target, methodname, nary)
        else:
            setattr(target, methodname, lambda A: UnaryExpr(A, op))


def _defer_operations_of(cls, allowed_categories='all'):
    if allowed_categories == 'all':
        allowed_categories = AllCategories

    else:
        allowed_categories = list(set(allowed_categories)) # remove duplicates
        assert all((category in AllCategories) for category in allowed_categories) # sanity check

    allowed_binary_operations = sum((BinaryOperationsByCategory[category] for category in allowed_categories), [])
    allowed_binary_reverse_operations = sum((BinaryReverseOperationsByCategory[category] for category in allowed_categories), [])
    allowed_unary_operations  = sum((UnaryOperationsByCategory[category]  for category in allowed_categories), [])

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
        _defer_method(cls, methodname, binary_op, is_binary=True, swap_binary_arguments=True)

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

