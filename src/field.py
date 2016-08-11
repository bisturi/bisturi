import time

class Field(object):
   def __init__(self):
      self.ctime = time.time()

   def compile(self):
      del self.ctime

   def init(self, packet, field_name, defaults):
      raise NotImplementedError()

   '''def __get__(self, instance, owner):
      raise NotImplementedError()

   def __set__(self, instance, obj):
      raise NotImplementedError()
      '''


class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianess='big', default=0):
      Field.__init__(self)
      self.default = default

   def init(self, packet, field_name, defaults):
      setattr(packet, field_name, defaults.get(field_name, self.default))


class Data(Field):
   def __init__(self, byte_count, default=''):
      Field.__init__(self)
      self.default = default

   def init(self, packet, field_name, defaults):
      setattr(packet, field_name, defaults.get(field_name, self.default))
