import time, struct, sys, copy

class Field(object):
   def __init__(self):
      self.ctime = time.time()

   def compile(self, field_name, position, fields):
      del self.ctime
      self.field_name = field_name
      #self.getval = lambda packet: getattr(packet, field_name)
      #self.setval = lambda packet, val: setattr(packet, field_name, val)

   def getval(self, packet): #TODO do this INLINE!!
      return getattr(packet, self.field_name)

   def setval(self, packet, val):
      return setattr(packet, self.field_name, val)

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, copy.deepcopy(self.default)))

   def unpack(self, packet, raw, offset=0):
      raise NotImplementedError()

   def pack(self, packet):
      raise NotImplementedError()

   def repeated(self, count=None, until=None, when=None):
      assert not (count is None and until is None)
      assert not (count is not None and until is not None)

      return Sequence(prototype=self, count=count, until=until, when=when)


   def when(self, condition):
      return Sequence(prototype=self, count=1, until=None, when=condition)


def _get_count(count_arg):
   if count_arg is None:
      return None

   if isinstance(count_arg, (int, long)):
      return lambda p: count_arg

   if isinstance(count_arg, Field):
      return lambda p: count_arg.getval(p)

   if callable(count_arg):
      return count_arg

   raise Exception("Invalid argument for a 'count'. Expected a number, a field or a callable.")

def _get_until(count, until):
   assert not (count is None and until is None)
   assert (count is None or until is None)

   if count is not None: #fixed
      class _Until(object):
         counter = 0
         
         def __call__(self, packet, *args):
            _Until.counter += 1
            if _Until.counter >= count(packet):
               return True
            else:
               return False

         def reset(self):
            _Until.counter = 0

      return _Until()
   
   else:
      assert callable(until)

      class _Until(object):
         def __call__(self, *args, **kargs):
            return until(*args, **kargs)
         def reset(self):
            pass

      return _Until()

def _get_when(count, when):
   if count is not None and when is None: #fixed
      def when_condition(packet, *args):
         return count(packet) > 0

   elif count is not None and when is not None: #fixed but conditional
      assert callable(when)
      def when_condition(packet, *args):
         return count(packet) > 0 and when(packet, *args)

   elif count is None and when is not None:
      assert callable(when)
      when_condition = when

   else:
      assert count is None and when is None
      when_condition = None

   return when_condition
      

class Sequence(Field):
   def __init__(self, prototype, count, until, when):
      Field.__init__(self)
      self.ctime = prototype.ctime
      self.default = []

      self.prototype = prototype

      resolved_count = _get_count(count)
      self.when = _get_when(resolved_count, when)
      self.until_condition = _get_until(resolved_count, until)

      from packet import Packet
      class Element(Packet):
         val = copy.deepcopy(self.prototype)

      self._Element = Element
      

   def unpack(self, packet, raw, offset=0):
      self.until_condition.reset()

      sequence = [] 
      self.setval(packet, sequence)
      stop = False if self.when is None else not self.when(packet, raw, offset)

      while not stop:
         elem = self._Element()
         offset = elem.unpack(raw, offset)

         sequence.append(elem.val)

         stop = self.until_condition(packet, raw, offset)

      self.setval(packet, sequence)
      return offset


   def pack(self, packet):
      sequence = self.getval(packet)
      raw = []
      for val in sequence:
         elem = self._Element()
         elem.val = val

         raw.append(elem.pack())

      return "".join(raw)


class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianess='big', default=0):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count
      self.is_signed = signed
      self.is_bigendian = (endianess in ('big', 'network')) or (endianess == 'local' and sys.byteorder == 'big')

   def compile(self, field_name, position, fields):
      Field.compile(self, field_name, position, fields)
      
      if self.byte_count in (1, 2, 4, 8): 
         code = {1:'B', 2:'H', 4:'I', 8:'Q'}[self.byte_count]
         if self.is_signed:
            code = code.lower()

         fmt = (">" if self.is_bigendian else "<") + code
         s = struct.Struct(fmt)
         del self.is_bigendian
         del self.is_signed

         def _unpack(raw_data):
            return s.unpack(raw_data)[0]

         def _pack(integer):
            return s.pack(integer)

      else:
         base = 2**(self.byte_count*8) 
         xcode = ("%0" + str(self.byte_count*2) + "x")
         def _unpack(raw_data):
            if not self.is_bigendian:
               raw_data = raw_data[::-1]
            
            num = int(raw_data.encode('hex'), 16)
            if self.is_signed and ord(raw_data[0]) > 127:
               num = -(base - num)

            return num

         def _pack(integer):
            num = (base + integer) if integer < 0 else integer

            data = (xcode % num).decode('hex')
            if not self.is_bigendian:
               data = data[::-1]

            return data

      self._unpack = _unpack
      self._pack = _pack


   def unpack(self, packet, raw, offset=0):
      raw_data = raw[offset:offset+self.byte_count]
      integer = self._unpack(raw_data)
      self.setval(packet, integer)

      return self.byte_count + offset

   def pack(self, packet):
      integer = self.getval(packet)
      raw = self._pack(integer)

      return raw


class Data(Field):
   def __init__(self, byte_count, include_delimiter=False, consume_delimiter=True, default=''):
      Field.__init__(self)
      self.default = default
      if not default and isinstance(byte_count, (int, long)):
         self.default = "\x00" * byte_count
      self.byte_count = byte_count
      self.include_delimiter = include_delimiter
      self.delimiter_to_be_included = self.byte_count if isinstance(self.byte_count, basestring) and not include_delimiter else ''

      assert not (consume_delimiter == False and include_delimiter == True)
      self.consume_delimiter = consume_delimiter #XXX document this!


   def unpack(self, packet, raw, offset=0):
      byte_count = self.byte_count(packet) if callable(self.byte_count) and not isinstance(self.byte_count, Field) else self.byte_count
      extra_count = 0
      if isinstance(byte_count, int):
         count = byte_count
      elif isinstance(byte_count, basestring):
         if self.include_delimiter:
            count = raw[offset:].find(byte_count) + len(byte_count)
         else:
            count = raw[offset:].find(byte_count)
            if self.consume_delimiter:
               extra_count = len(byte_count)
            self.delimiter_to_be_included = byte_count

      elif hasattr(byte_count, 'search'):
         if byte_count.pattern == "$":    # shortcut
            count = len(raw) - offset

         else:
            match = byte_count.search(raw[offset:], 0) #XXX should be (raw, offset) or (raw[offset:], 0) ? See the method search in the module re
            if match:
               if self.include_delimiter:
                  count = match.end()
               else:
                  count = match.start()
                  if self.consume_delimiter:
                     extra_count = match.end()-count
                  self.delimiter_to_be_included = match.group()
            else:
               count = -1
      else:
         count = byte_count.getval(packet)

      if count < 0:
         raise IndexError()

      raw_data = raw[offset:offset+count]
      self.setval(packet, raw_data)

      return count + extra_count + offset

   def pack(self, packet):
      return self.getval(packet) + self.delimiter_to_be_included

class Ref(Field):
   def __init__(self, referenced, *packet_field_args, **packet_field_kargs):
      Field.__init__(self)

      self.require_updated_packet_instance = False
      from packet import Packet
      if isinstance(referenced, type) and issubclass(referenced, Field):
         def get_packet_instance(packet):
            class FieldReferenced(Packet):
               val = referenced(*packet_field_args, **packet_field_kargs)

            return FieldReferenced()

      elif isinstance(referenced, type) and issubclass(referenced, Packet):
         def get_packet_instance(packet):
            return referenced(*packet_field_args, **packet_field_kargs)

      elif callable(referenced):
         self.require_updated_packet_instance = True
         def get_packet_instance(packet):
            i = referenced(packet)
            if isinstance(i, Field):
               class FieldReferenced(Packet):
                  val = i

               return FieldReferenced()
            else:
               return i #a packet instance

      else:
         raise ValueError("Unknow referenced object.")

      self.get_packet_instance = get_packet_instance


   def init(self, packet, defaults):
      if self.field_name in defaults:
         self.setval(packet, defaults[self.field_name])
      elif not self.require_updated_packet_instance:
         self.setval(packet, self.get_packet_instance(packet))

   def unpack(self, packet, raw, offset=0):
      if self.require_updated_packet_instance:
         self.setval(packet, self.get_packet_instance(packet))

      return self.getval(packet).unpack(raw, offset)

   def pack(self, packet):
      return self.getval(packet).pack()

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
      Field.compile(self, field_name, position, fields)

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
         I.compile(field_name="_bits__"+"_".join(reversed(name_of_members)), position=-1, fields=[])
   

   def init(self, packet, defaults):
      if self.iam_first:
         self.I.setval(packet, 0)

      Field.init(self, packet, defaults)


   def unpack(self, packet, raw, offset=0):
      if self.iam_first:
         offset = self.I.unpack(packet, raw, offset)

      I = self.I.getval(packet)

      self.setval(packet, (I & self.mask) >> self.shift)
      return offset

   def pack(self, packet):
      I = self.I.getval(packet)
      self.I.setval(packet, ((self.getval(packet) << self.shift) & self.mask) | (I & (~self.mask)))

      if self.iam_last:
         return self.I.pack(packet)
      else:
         return ""
      

class Bkpt(Field):
   def init(self, packet, defaults):
      pass

   def unpack(self, packet, raw, offset=0):
      import pdb
      pdb.set_trace()
      return offset

   def pack(self, packet):
      import pdb
      pdb.set_trace()
      return ""
