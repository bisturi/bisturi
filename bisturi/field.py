import time, struct, sys, copy, re
from packet import Packet, Prototype
from deferred import defer_operations_of, UnaryExpr, BinaryExpr, compile_expr_into_callable
from pattern_matching import Any
from fragments import FragmentsOfRegexps

def exec_once(m):
   ''' Force to execute the method M only once and save its result.
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
   def __init__(self):
      self.ctime = time.time()
      self.is_fixed = False
      self.struct_code = None
      self.is_bigendian = True

      self.move_arg = None
      self.movement_type = None

   def describe_yourself(self, field_name, bisturi_conf):
      if self.move_arg is None and 'align' in bisturi_conf:
         self.aligned(to=bisturi_conf['align'])

      if self.move_arg is None:
         return [(field_name, self)]

      else:
         return [("_shift_to_%s" % field_name, Move(self.move_arg, self.movement_type)), (field_name, self)]

   @exec_once
   def compile(self, field_name, position, fields, bisturi_conf):
      # Dont call this from a subclass. Call _compile directly.
      return self._compile(field_name, position, fields, bisturi_conf)

   def _compile(self, field_name, position, fields, bisturi_conf): 
      self.field_name = field_name

      return [field_name]

   def getval(self, packet): #TODO do this INLINE!!
      return getattr(packet, self.field_name)

   def setval(self, packet, val): #TODO do this INLINE!!
      return setattr(packet, self.field_name, val)

   def init(self, packet, defaults):
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
      return offset

   def pack_noop(self, pkt, fragments, **k):
      return fragments

   def repeated(self, count=None, until=None, when=None, default=None, aligned=None):
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
   def __init__(self, prototype, count, until, when, default=None, aligned=None):
      Field.__init__(self)
      assert isinstance(prototype, Field)

      self.ctime = prototype.ctime
      self.default = default if default is not None else []

      self.prototype_field = prototype
      self.aligned_to = aligned

      self.tmp = (count, until, when)

      
   @exec_once
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)
      if self.aligned_to is None:
          self.aligned_to = bisturi_conf.get('align', 1)

      # XXX we are propagating the 'align' attribute (in bisturi_conf) to
      # the prototype packet. This is valid ...but inelegant
      # This happen in others fields like Optional and Ref
      self.seq_elem_field_name = "_seq_elem__"+field_name
      self.prototype_field.compile(field_name=self.seq_elem_field_name, position=-1, fields=[], bisturi_conf=bisturi_conf)

      count, until, when = self.tmp

      if isinstance(count, (UnaryExpr, BinaryExpr)):
         count = compile_expr_into_callable(count)

      #if isinstance(until, (UnaryExpr, BinaryExpr)):
      #   until = compile_expr_into_callable(until)
      
      if isinstance(when, (UnaryExpr, BinaryExpr)):
         when = compile_expr_into_callable(when)

      self.resolved_count = None if count is None else _get_count(count)
      self.when = _get_when(self.resolved_count, when)
      self.until_condition = _get_until(self.resolved_count, until)

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
      _unpack = self.prototype_field.unpack
      _append = sequence.append
      _until  = self.until_condition
      _aligned_to = self.aligned_to
      while not stop:
         offset += (_aligned_to - (offset % _aligned_to)) % _aligned_to
         offset =  _unpack(pkt=pkt, raw=raw, offset=offset, **k)

         obj = getattr(pkt, seq_elem_field_name) 
         
         _append(obj)
         stop = _until(pkt=pkt, raw=raw, offset=offset, **k)

         if isinstance(obj, Packet):
             # if this is a Packet instance, obj is the same object each iteration, 
             # so we need a copy, a fresh object for the next round
             setattr(pkt, seq_elem_field_name, obj.__class__(_initialize_fields=False))
         elif not isinstance(obj, (int, long, basestring)): 
             # Other object no constant should be copied too: TODO will this work all the times?
             setattr(pkt, seq_elem_field_name, copy.deepcopy(obj))


      # self.setval(pkt, sequence), we don't need this, because the sequence is already there
      return offset


   def pack(self, pkt, fragments, **k):
      sequence = getattr(pkt, self.field_name)
      seq_elem_field_name = self.seq_elem_field_name
      _aligned_to = self.aligned_to
      for val in sequence:
         setattr(pkt,  seq_elem_field_name, val)
         fragments.current_offset += (_aligned_to - (fragments.current_offset % _aligned_to)) % _aligned_to
         self.prototype_field.pack(pkt, fragments, **k)

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
          
          if self.resolved_count is None:
              fragments.append("(%s)*" % subregexp, is_literal=False)
          else:
              fragments.append("(%s){%i}" % (subregexp, self.resolved_count), is_literal=False)

      return fragments


class Optional(Field):
   def __init__(self, prototype, when, default=None):
      Field.__init__(self)
      assert isinstance(prototype, Field)

      self.ctime = prototype.ctime
      self.default = default

      self.prototype_field = prototype
      self.tmp = when

      
   @exec_once
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)
      self.opt_elem_field_name = "_opt_elem__"+field_name
      self.prototype_field.compile(field_name=self.opt_elem_field_name, position=-1, fields=[], bisturi_conf=bisturi_conf)

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

@defer_operations_of
class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianness=None, default=0):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count
      self.endianness = endianness
      self.is_signed = signed
      self.is_fixed = True

   @exec_once
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)
      
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
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)

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
                 fragments.append(".{%i}" % byte_count, is_literal=False)
             else:
                 fragments.append(".*", is_literal=False)

          else:
             if isinstance(self.until_marker, basestring):
                 fragments.append(".*?%s" % re.escape(self.until_marker), is_literal=False)

             elif hasattr(self.until_marker, 'search'):
                 fragments.append(self.until_marker.pattern, is_literal=False)
             
             else:
                assert False

      return fragments

class Ref(Field):
   def __init__(self, prototype, default=None, embeb=False): # TODO we don't support Bits fields
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

      if embeb and not isinstance(self.prototype, Packet):
         raise ValueError("The prototype must be a Packet if you want to embeb it.")
            
      self.embeb = embeb 
      # TODO :
      # class D(Packet):
      #    i = Int()
      # class A(Packet):
      #    d = Ref(D, embeb=True)
      #
      # a = A()
      # a.i    has the correct value
      # a.d.i  has the default value of an Int which it is wrong.
      #        we need to do something with this case.
   
   def describe_yourself(self, field_name, bisturi_conf):
      desc = Field.describe_yourself(self, field_name, bisturi_conf)
      if self.embeb:
         desc.extend([(fname, f) for fname, f, _, _ in self.prototype.get_fields()])

      return desc

   @exec_once
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)

      self.position = position
      if isinstance(self.prototype, Field): 
         self.prototype.compile(field_name=field_name, position=position, fields=[], bisturi_conf=bisturi_conf)

      prototype = self.prototype
      if isinstance(prototype, Field):
         self.unpack = prototype.unpack
         self.pack   = prototype.pack

      elif isinstance(prototype, Packet):
         self.unpack = self._unpack_referencing_a_packet
         self.pack   = self._pack_referencing_a_packet
         self.prototype = prototype.as_prototype()

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
      return slots
      

   def init(self, packet, defaults):   #TODO ver el tema de los defaults q viene de la instanciacion del packet
      # we use our prototype to get a valid default if the prototype is not a callable
      # in the other case, we use self.default.
      prototype = self.prototype
      if isinstance(prototype, Field):
         prototype.init(packet, defaults)

      elif isinstance(prototype, Prototype):
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
         referenced.compile(field_name=self.field_name, position=self.position, fields=[], bisturi_conf={})
         referenced.init(pkt, {})

         return referenced.unpack(pkt=pkt, raw=raw, offset=offset, **k)

      assert isinstance(referenced, Packet)

      setattr(pkt, self.field_name, referenced)
      return referenced.unpack_impl(raw, offset, **k)

   def _pack_with_callable(self, pkt, fragments, **k):
      obj = getattr(pkt, self.field_name)  # this can be a Packet or can be anything (but not a Field: it could be a 'int' for example but not a 'Int')
      if isinstance(obj, Packet):
         return obj.pack_impl(fragments=fragments, **k)

      # TODO: raise NotImplementedError("We don't know how to pack this. The field '%s' (type '%s') is not a Packet neither the Ref's prototype is a Field/Packet (it is a '%s'). Probably the Ref's prototype is a callable, right? Because that we can't know how to pack this field (which is not pointing to a Packet instance) because we cannot execute the callable during the packing-time." % (self.field_name, str(type(obj)), str(type(self.prototype))))

      # we try to know how to pack this value
      assert callable(self.prototype)
      referenced = self.prototype(pkt=pkt, fragments=fragments, packing=True, **k)   # TODO add more parameters, like raw=partial_raw

      if isinstance(referenced, Field):
         referenced.compile(field_name=self.field_name, position=self.position, fields=[], bisturi_conf={})
         #referenced.init(pkt, {})

         return referenced.pack(pkt, fragments, **k)

      # well, we are in a dead end: the 'obj' object IS NOT a Packet, it is a "primitive" value
      # however, the 'referenced' object IS a Packet and we cannot do anything else
      raise NotImplementedError()


   def _unpack_referencing_a_packet(self, pkt, **k):
      p = getattr(pkt, self.field_name, None)
      if p is not None:
          return p.unpack_impl(**k)

      # Workaround if the init method wasn't call
      setattr(pkt, self.field_name, self.prototype.clone())
      return getattr(pkt, self.field_name).unpack_impl(**k)

   def _pack_referencing_a_packet(self, pkt, fragments, **k):
      return getattr(pkt, self.field_name).pack_impl(fragments=fragments, **k)
 

@defer_operations_of
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
   def compile(self, field_name, position, fields, bisturi_conf):
      slots = Field._compile(self, field_name, position, fields, bisturi_conf)

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
         I.compile(field_name=fname, position=-1, fields=[], bisturi_conf={})

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
              start = k['stack'][-1].offset
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
              start = k['stack'][-1].offset
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
   def compile(self, field_name, position, fields, bisturi_conf):
      return []

   def unpack(self, pkt, raw, offset=0, **k):
      return offset

   def pack(self, pkt, fragments, **k):
      fragments.append("")
      return fragments
