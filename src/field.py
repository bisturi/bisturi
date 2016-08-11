import time, struct, sys

class Field(object):
   def __init__(self):
      self.ctime = time.time()

   def compile(self, field_name):
      del self.ctime
      self.field_name = field_name
      self.getval = lambda packet: getattr(packet, field_name)
      self.setval = lambda packet, val: setattr(packet, field_name, val)


   def init(self, packet, field_name, defaults):
      raise NotImplementedError()

   def from_raw(self, packet, raw, offset=0):
      raise NotImplementedError()



class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianess='big', default=0):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count
      self.is_signed = signed
      self.is_bigendian = (endianess in ('big', 'network')) or (endianess == 'local' and sys.byteorder == 'big')

   def compile(self, field_name):
      Field.compile(self, field_name)
      
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

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, self.default))

   def from_raw(self, packet, raw, offset=0):
      raw_data = raw[offset:offset+self.byte_count]
      integer = self._unpack(raw_data)
      self.setval(packet, integer)

      return self.byte_count

   def to_raw(self, packet):
      integer = self.getval(packet)
      raw = self._pack(integer)

      return raw


class Data(Field):
   def __init__(self, byte_count, include_delimiter=False, default=''):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count
      self.include_delimiter = include_delimiter
      self.delimiter_to_be_included = self.byte_count if isinstance(self.byte_count, basestring) and not include_delimiter else ''

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, self.default))

   def from_raw(self, packet, raw, offset=0):
      byte_count = self.byte_count(packet) if callable(self.byte_count) and not isinstance(self.byte_count, Field) else self.byte_count
      extra_count = 0
      if isinstance(byte_count, int):
         count = byte_count
      elif isinstance(byte_count, basestring):
         if self.include_delimiter:
            count = raw[offset:].find(byte_count) + len(byte_count)
         else:
            count = raw[offset:].find(byte_count)
            extra_count = len(byte_count)
            self.delimiter_to_be_included = byte_count

      elif hasattr(byte_count, 'search'):
         match = byte_count.search(raw, offset)
         if match:
            if self.include_delimiter:
               count = match.end()
            else:
               count = match.start()
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

      return count + extra_count

   def to_raw(self, packet):
      return self.getval(packet) + self.delimiter_to_be_included
