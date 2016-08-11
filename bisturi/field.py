import time, struct, sys, copy
from packet import Packet
from deferred import defer_operations_of, UnaryExpr, BinaryExpr, compile_expr_into_callable

class Field(object):
   def __init__(self):
      self.ctime = time.time()
      self.is_fixed = False
      self.struct_code = None
      self.is_bigendian = True

   def compile(self, field_name, position, fields):
      del self.ctime
      self.field_name = field_name

      return [field_name]

   def getval(self, packet): #TODO do this INLINE!!
      return getattr(packet, self.field_name)

   def setval(self, packet, val): #TODO do this INLINE!!
      return setattr(packet, self.field_name, val)

   def init(self, packet, defaults):
      #import pdb; pdb.set_trace()
      setattr(packet, self.field_name, defaults.get(self.field_name, copy.deepcopy(self.default))) # if isinstance(self.default, (int, long, basestring)) else (copy.deepcopy(self.default))))

   def unpack(self, pkt, raw, offset, **k):
      raise NotImplementedError()

   def pack(self, packet):
      raise NotImplementedError()

   def repeated(self, count=None, until=None, when=None, default=None):
      assert not (count is None and until is None)
      assert not (count is not None and until is not None)

      return Sequence(prototype=self, count=count, until=until, when=when, default=default)


   def when(self, condition, default=None):
      return Optional(prototype=self, when=condition, default=default)


def _get_count(count_arg):
   '''Return a callable from count_arg so you can invoke that callable
      and the count of byte will be retrived. 
      If count_arg is a callable, it must accept any variable keyword-argument.'''

   if isinstance(count_arg, (int, long)):
      return lambda **k: count_arg

   if isinstance(count_arg, Field):
      return lambda pkt, **k: getattr(pkt, count_arg.field_name)

   if callable(count_arg):
      return count_arg

   raise Exception("Invalid argument for a 'count'. Expected a number, a field or a callable.")

def _get_until(count, until):
   '''Return a callable that will return True or False if the stream ends or
      doesn't end (this will depend on the 'until' paramenter or the parameter 'count')
      If 'count' and 'until' aren't None, they must be callables, however,
      if one is not None, the other must be None.
      Both 'count' and 'until' (if are callable), they must accept any variable keyword-argument.'''
   assert not (count is None and until is None)
   assert (count is None or until is None)

   if count is not None: # fixed size: no 'until' condition
      class _Until(object):
         counter = 0
         
         def __call__(self, **k):
            _Until.counter += 1
            if _Until.counter >= count(**k):
               return True
            else:
               return False

         def reset(self):
            _Until.counter = 0

      return _Until()
   
   else:
      assert callable(until)

      class _Until(object):
         def __call__(self, **k):
            return until(**k)

         def reset(self):
            pass

      return _Until()

def _get_when(count, when):
   '''Like _get_until, this will return a callable.
      At difference with _get_until, both 'count' and 'when' can be
      callables at the same time or Nones at the same time or any combination. '''

   if count is not None and when is None: # condition from a count-byte
      def when_condition(**k):
         return count(**k) > 0

   elif count is not None and when is not None: # a more variable condition
      assert callable(when)
      def when_condition(**k):
         return count(**k) > 0 and when(**k)

   elif count is None and when is not None:
      assert callable(when)
      when_condition = when

   else:
      assert count is None and when is None
      when_condition = None

   return when_condition
      

class Sequence(Field):
   def __init__(self, prototype, count, until, when, default=None):
      Field.__init__(self)
      self.ctime = prototype.ctime
      self.default = default if default is not None else []

      self.prototype_field = prototype

      self.tmp = (count, until, when)

      
   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)
      self.seq_elem_field_name = "_seq_elem__"+field_name
      self.prototype_field.compile(field_name=self.seq_elem_field_name, position=-1, fields=[])

      count, until, when = self.tmp
      del self.tmp

      if isinstance(count, (UnaryExpr, BinaryExpr)):
         count = compile_expr_into_callable(count)

      #if isinstance(until, (UnaryExpr, BinaryExpr)):
      #   until = compile_expr_into_callable(until)
      
      if isinstance(when, (UnaryExpr, BinaryExpr)):
         when = compile_expr_into_callable(when)

      resolved_count = None if count is None else _get_count(count)
      self.when = _get_when(resolved_count, when)
      self.until_condition = _get_until(resolved_count, until)

      return slots + [self.seq_elem_field_name]

   def init(self, packet, defaults):
      Field.init(self, packet, defaults)
      self.prototype_field.init(packet, {})
      
   def unpack(self, pkt, raw, offset=0, **k):
      self.until_condition.reset()

      sequence = [] 
      setattr(pkt, self.field_name, sequence) # clean up the previous sequence, so it can be used by the 'when' and 'until' callbacks
      stop = False if self.when is None else not self.when(pkt=pkt, raw=raw, offset=offset, **k)

      seq_elem_field_name = self.seq_elem_field_name
      while not stop:
         offset = self.prototype_field.unpack(pkt=pkt, raw=raw, offset=offset, **k)

         obj = getattr(pkt, seq_elem_field_name) # if this is a Packet instance, obj is the same object each iteration, so we need a copy
         if isinstance(obj, Packet):
            avoid_deep_copies = obj.__bisturi__.get('avoid_deep_copies', True)

            if avoid_deep_copies:
               obj = copy.copy(obj)
            else:
               obj = copy.deepcopy(obj)

         sequence.append(obj)
         stop = self.until_condition(pkt=pkt, raw=raw, offset=offset, **k)

      # self.setval(pkt, sequence), we don't need this, because the sequence is already there
      return offset


   def pack(self, packet):
      sequence = getattr(packet, self.field_name)
      raw = []
      seq_elem_field_name = self.seq_elem_field_name
      for val in sequence:
         setattr(packet,  seq_elem_field_name, val)
         raw.append(self.prototype_field.pack(packet))

      return "".join(raw)


class Optional(Field):
   def __init__(self, prototype, when, default=None):
      Field.__init__(self)
      self.ctime = prototype.ctime
      self.default = default

      self.prototype_field = prototype
      self.tmp = when

      
   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)
      self.opt_elem_field_name = "_opt_elem__"+field_name
      self.prototype_field.compile(field_name=self.opt_elem_field_name, position=-1, fields=[])

      when = self.tmp
      del self.tmp
      
      if isinstance(when, (UnaryExpr, BinaryExpr)):
         when = compile_expr_into_callable(when)

      self.when = _get_when(None, when)
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
         if isinstance(obj, Packet):
            avoid_deep_copies = obj.__bisturi__.get('avoid_deep_copies', True)

            if avoid_deep_copies:
               obj = copy.copy(obj)
            else:
               obj = copy.deepcopy(obj)

      setattr(pkt, self.field_name, obj)
      return offset


   def pack(self, packet):
      obj = getattr(packet, self.field_name)
      opt_elem_field_name = self.opt_elem_field_name
      if obj is not None:
         setattr(packet,  opt_elem_field_name, obj)
         return self.prototype_field.pack(packet)

      else:
         return ""

@defer_operations_of
class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianess='big', default=0):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count
      self.is_signed = signed
      self.is_bigendian = (endianess in ('big', 'network')) or (endianess == 'local' and sys.byteorder == 'big')
      self.is_fixed = True

   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)
      
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

   def unpack(self, pkt, raw, offset=0, **k):
      raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

   def pack(self, packet):
      raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

   def _unpack_fixed_and_primitive_size(self, pkt, raw, offset=0, **k):
      next_offset = offset + self.byte_count
      integer = self.struct_obj.unpack(raw[offset:next_offset])[0]
      setattr(pkt, self.field_name, integer)

      return next_offset

   def _pack_fixed_and_primitive_size(self, pkt):
      integer = getattr(pkt, self.field_name)
      raw = self.struct_obj.pack(integer)

      return raw

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

   def _pack_fixed_size(self, pkt):
      integer = getattr(pkt, self.field_name)
      num = (self.base + integer) if integer < 0 else integer

      data = (self.xcode % num).decode('hex')
      if not self.is_bigendian:
         data = data[::-1]

      return data

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

   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)

      if self.byte_count is not None:
         if isinstance(self.byte_count, (int, long)):
            self.struct_code = "%is" % self.byte_count
            self.unpack = self._unpack_fixed_size
         
         elif isinstance(self.byte_count, Field):
            self.unpack = self._unpack_variable_size_field

         elif callable(self.byte_count):
            self.unpack = self._unpack_variable_size_callable

         elif isinstance(self.byte_count, (UnaryExpr, BinaryExpr)):
            self.byte_count = compile_expr_into_callable(self.byte_count)
            self.unpack = self._unpack_variable_size_callable

         else:
            assert False

      else:
         if isinstance(self.until_marker, basestring):
            self.unpack = self._unpack_with_string_marker

         elif hasattr(self.until_marker, 'search'):
            self.unpack = self._unpack_with_regexp_marker
         
         else:
            assert False

      return slots

   def unpack(self, pkt, raw, offset=0, **k):
      raise NotImplementedError("This method should be implemented during the 'compilation' phase.")

   def pack(self, packet):
      return getattr(packet, self.field_name) + self.delimiter_to_be_included

   def _unpack_fixed_size(self, pkt, raw, offset=0, **k):
      next_offset = offset + self.byte_count
      setattr(pkt, self.field_name, raw[offset:next_offset])
      
      return next_offset
   
   def _unpack_variable_size_field(self, pkt, raw, offset=0, **k):
      next_offset = offset + getattr(pkt, self.byte_count.field_name)
      setattr(pkt, self.field_name, raw[offset:next_offset])
      
      return next_offset
   
   def _unpack_variable_size_callable(self, pkt, raw, offset=0, **k):
      next_offset = offset + self.byte_count(pkt=pkt, raw=raw, offset=offset, **k)
      setattr(pkt, self.field_name, raw[offset:next_offset])
      
      return next_offset

   def _unpack_with_string_marker(self, pkt, raw, offset=0, **k):
      until_marker = self.until_marker
      count = raw[offset:].find(until_marker)
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
      extra_count = 0
      if until_marker.pattern == "$":    # shortcut
         count = len(raw) - offset
      else:
         match = until_marker.search(raw[offset:], 0) #XXX should be (raw, offset) or (raw[offset:], 0) ? See the method search in the module re
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

class Ref(Field):
   def __init__(self, prototype, default=None): # TODO we don't support Bits fields
      Field.__init__(self)

      self.prototype = prototype # TODO should we copy this prototype and/or its default?
      self.default = default

      if isinstance(self.prototype, type):
         self.prototype = self.prototype() # get an object
      

      if callable(self.prototype) and default is None:
         raise ValueError("We need a default object!")

      if not callable(self.prototype) and default is not None:
         raise ValueError("We don't need a default object, we will be using the prototype object instead.")

      if self.default is None:
         if isinstance(self.prototype, Packet):
            self.default = self.prototype
         else:
            assert isinstance(self.prototype, Field)
            self.default = getattr(self.prototype, 'default', None)
            


   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)

      self.position = position
      if isinstance(self.prototype, Field): 
         self.prototype.compile(field_name=field_name, position=position, fields=[])

      prototype = self.prototype
      if isinstance(prototype, Field):
         self.unpack = prototype.unpack
         self.pack   = prototype.pack

      elif isinstance(prototype, Packet):
         self.unpack = self._unpack_referencing_a_packet
         self.pack   = self._pack_referencing_a_packet 

      else:
         assert callable(self.prototype)
         pass

      return slots
      

   def init(self, packet, defaults):   #TODO ver el tema de los defaults q viene de la instanciacion del packet
      # we use our prototype to get a valid default if the prototype is not a callable
      # in the other case, we use self.default.
      prototype = self.prototype
      if isinstance(prototype, Field):
         prototype.init(packet, defaults)

      elif isinstance(prototype, Packet):
         if self.field_name not in defaults:
            defaults[self.field_name] = copy.deepcopy(prototype)  # get a new instance (Field.init will copy that object)

         Field.init(self, packet, defaults)

      else:
         assert callable(self.prototype)
         default = self.default
         if isinstance(default, Packet):
            if self.field_name not in defaults:
               defaults[self.field_name] = copy.deepcopy(default)  # get a new instance (Field.init will copy that object)

         Field.init(self, packet, defaults)


   def unpack(self, pkt, raw, offset=0, **k):
      if callable(self.prototype):
         referenced = self.prototype(pkt=pkt, raw=raw, offset=offset, **k)
      else:
         referenced = self.prototype

      if isinstance(referenced, Field):
         referenced.compile(field_name=self.field_name, position=self.position, fields=[])
         referenced.init(pkt, {})

         return referenced.unpack(pkt=pkt, raw=raw, offset=offset, **k)

      assert isinstance(referenced, Packet)

      setattr(pkt, self.field_name, referenced)
      return referenced.unpack(raw, offset, **k)


   def pack(self, packet):
      if isinstance(self.prototype, Field):
         return self.prototype.pack(packet)

      obj = getattr(packet, self.field_name)  # this can be a Packet or can be anything (but not a Field: it could be a 'int' for example but not a 'Int')
      if isinstance(obj, Packet):
         return obj.pack()

      # we try to know how to pack this value
      assert callable(self.prototype)
      referenced = self.prototype(pkt=packet, packing=True)   # TODO add more parameters, like raw=partial_raw

      if isinstance(referenced, Field):
         referenced.compile(field_name=self.field_name, position=self.position, fields=[])
         #referenced.init(packet, {})

         return referenced.pack(packet)

      # well, we are in a dead end: the 'obj' object IS NOT a Packet, it is a "primitive" value
      # however, the 'referenced' object IS a Packet and we cannot do anything else
      raise NotImplementedError()

   def _unpack_referencing_a_packet(self, pkt, **k):
      return getattr(pkt, self.field_name).unpack(**k)

   def _pack_referencing_a_packet(self, packet):
      return getattr(packet, self.field_name).pack()
 
   def _pack_referencing_a_unknow_object(self, packet):     
      obj = getattr(packet, self.field_name)  # this can be a Packet or can be anything (but not a Field: it could be a 'int' for example but not a 'Int')
      if isinstance(obj, Packet):
         return obj.pack()

      # we try to know how to pack this "primitive" value
      referenced = self.prototype(pkt=packet, packing=True)   # TODO add more parameters, like raw=partial_raw

      if isinstance(referenced, Field):
         referenced.compile(field_name=self.field_name, position=self.position, fields=[])
         return referenced.pack(packet)

      # well, we are in a dead end: the 'obj' object IS NOT a Packet, it is a "primitive" value
      # however, the 'referenced' object IS a Packet and we cannot do anything else
      raise NotImplementedError()

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
   
   def compile(self, field_name, position, fields):
      slots = Field.compile(self, field_name, position, fields)

      if position == 0 or not isinstance(fields[position-1][1], Bits):
         self.iam_first = True

      if position == len(fields)-1 or not isinstance(fields[position+1][1], Bits):
         self.iam_last = True

      if self.iam_last:
         cumshift = 0
         I = Int()
         name_of_members = []
         seq = []
         for n, f in reversed(fields[:position+1]):
            if not isinstance(f, Bits):
               break

            f.shift = cumshift
            f.mask = ((2**f.bit_count) - 1) << f.shift
            f.I = I

            name_of_members.append(n)
            seq.append(f.bit_count)
            
            cumshift += f.bit_count
            del f.bit_count

         if not (cumshift % 8 == 0):
            raise Bits.ByteBoundaryError("Wrong sequence of bits: %s with total sum of %i (not a multiple of 8)." % (str(list(reversed(seq))), cumshift))

         I.byte_count = cumshift / 8
         fname = "_bits__"+"_".join(reversed(name_of_members))
         I.compile(field_name=fname, position=-1, fields=[])

         slots.append(fname)
      return slots


   def init(self, packet, defaults):
      if self.iam_first:
         setattr(packet, self.I.field_name, 0)

      Field.init(self, packet, defaults)


   def unpack(self, pkt, raw, offset=0, **k):
      if self.iam_first:
         offset = self.I.unpack(pkt, raw, offset, **k)

      I = getattr(pkt, self.I.field_name)

      setattr(pkt, self.field_name, (I & self.mask) >> self.shift)
      return offset

   def pack(self, packet):
      I = getattr(packet, self.I.field_name)
      setattr(packet, self.I.field_name, ((getattr(packet, self.field_name) << self.shift) & self.mask) | (I & (~self.mask)))

      if self.iam_last:
         return self.I.pack(packet)
      else:
         return ""
      

class Bkpt(Field):
   def init(self, packet, defaults):
      pass

   def unpack(self, pkt, raw, offset=0, **k):
      import pdb
      pdb.set_trace()
      return offset

   def pack(self, packet):
      import pdb
      pdb.set_trace()
      return ""
