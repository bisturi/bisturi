import collections, functools

BinaryExpr = collections.namedtuple('BinaryExpr', ['l', 'r', 'op'])
UnaryExpr = collections.namedtuple('UnaryExpr', ['r', 'op'])

def compile_expr(root_expr, args=None, ops=None):
   from field import Field

   if args is None:
      args = []
      ops = []

   if not isinstance(root_expr, (UnaryExpr, BinaryExpr, Field)):
      args.append(root_expr)
   
   elif isinstance(root_expr, BinaryExpr):
      l, r, op = root_expr
      compile_expr(l, args, ops)
      compile_expr(r, args, ops)
      ops.append((2,op))

   elif isinstance(root_expr, UnaryExpr):
      r, op = root_expr
      compile_expr(r, args, ops)
      ops.append((1,op))

   else:
      field_name = root_expr.field_name
      ops.append((0, lambda pkt, *vargs, **kargs: getattr(pkt, field_name)))

   return args, ops

def exec_compiled_expr(pkt, args, ops, *vargs, **kargs):
   args = list(args)
   for arg_count, op in ops:
      if arg_count == 0:
         result = op(pkt, *vargs, **kargs)
      else:
         result = op(*args[:arg_count])
         del args[:arg_count]
      args.insert(0, result)

   assert len(args) == 1
   return args[0]

def compile_expr_into_callable(root_expr):
   args, ops = compile_expr(root_expr)
   return lambda pkt, *vargs, **kargs: exec_compiled_expr(pkt, args, ops, *vargs, **kargs)
   

import operator
def _defer_method(target, methodname, op, is_binary):
   if is_binary:
      setattr(target, methodname, lambda A, B: BinaryExpr(A, B, op))
   else:
      setattr(target, methodname, lambda A: UnaryExpr(A, op))
   

def defer_operations_of(cls):
   # TODO - revisar todos los nombres
   for binary_op in [
            # arith ------------------------------------
            operator.add,         operator.sub,
            operator.mul,         operator.div,
            operator.truediv,     operator.floordiv,
            operator.mod,         operator.pow,

            # cmp --------------------------------------
            operator.le,          operator.lt,
            operator.ge,          operator.gt,
            operator.eq,          operator.ne,

            # logical ----------------------------------
            operator.and_,        operator.or_,
            operator.xor,              
            operator.rshift,      operator.lshift,
            ]:
      
      op_name = binary_op.__name__
      if op_name.endswith("_"):
         op_name = op_name[:-1]

      methodname = "__%s__" % op_name
      _defer_method(cls, methodname, binary_op, is_binary=True)
   
   for unary_op in [
            # arith ------------------------------------
            operator.neg,

            # logical ----------------------------------
            operator.not_,        operator.inv,
            ]:
      
      op_name = unary_op.__name__
      if op_name.endswith("_"):
         op_name = op_name[:-1]

      if op_name == "inv":
         op_name = "invert"

      methodname = "__%s__" % op_name
      _defer_method(cls, methodname, unary_op, is_binary=False)
   
   return cls

UnaryExpr = defer_operations_of(UnaryExpr)
BinaryExpr = defer_operations_of(BinaryExpr)
