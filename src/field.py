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
      self.base = 2**(byte_count*8) - 1 #base minus 1

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, self.default))

   def from_raw(self, packet, raw, offset=0):
      raw_data = raw[offset:offset+self.byte_count]

      if self.byte_count in (1, 2, 4, 8): 
         code = {1:'B', 2:'H', 4:'I', 8:'Q'}[self.byte_count]
         if self.is_signed:
            code.lowercase()

         fmt = (">" if self.is_bigendian else "<") + code
         s = struct.Struct(fmt)

         integer = s.unpack(raw_data)[0]

      else:
         if not self.is_bigendian:
            raw_data = raw_data[::-1]
         
         num = int(raw_data.encode('hex'), 16)
         if self.is_signed and ord(raw_data[0]) > 127:
            num = -(self.base - num)

         integer = num

      self.setval(packet, integer)

      return self.byte_count

   def to_raw(self, packet):
      integer = self.getval(packet)
      if self.byte_count in (1, 2, 4, 8): 
         code = {1:'B', 2:'H', 4:'I', 8:'Q'}[self.byte_count]
         if self.is_signed:
            code.lowercase()

         fmt = (">" if self.is_bigendian else "<") + code
         s = struct.Struct(fmt)

         raw = s.pack(integer)

      else:
         val = integer
         if val < 0:
            num = self.base + val + 1
         else:
            num = val

         data = (("%0" + str(self.byte_count*2) + "x") % num).decode('hex')
         if not self.is_bigendian:
            data = data[::-1]

         raw = data

      return raw


class Data(Field):
   def __init__(self, byte_count, default=''):
      Field.__init__(self)
      self.default = default
      self.byte_count = byte_count

   def init(self, packet, defaults):
      self.setval(packet, defaults.get(self.field_name, self.default))

   def from_raw(self, packet, raw, offset=0):
      if isinstance(self.byte_count, int):
         count = self.byte_count
      else:
         count = self.byte_count.getval(packet)

      raw_data = raw[offset:offset+count]
      self.setval(packet, raw_data)

      return count

   def to_raw(self, packet):
      return self.getval(packet)
