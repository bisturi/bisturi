import time

class Field(object):
   def __init__(self):
      self.ctime = time.time()

   def init(self, packet, field_name):
      del self.ctime

   '''def __get__(self, instance, owner):
      raise NotImplementedError()

   def __set__(self, instance, obj):
      raise NotImplementedError()
      '''


class Int(Field):
   def __init__(self, byte_count=4, signed=False, endianess='big'):
      Field.__init__(self)

   def init(self, packet, field_name):
      Field.init(self, packet, field_name)
      setattr(packet, field_name, 0)


class Data(Field):
   def __init__(self, byte_count):
      Field.__init__(self)

   def init(self, packet, field_name):
      Field.init(self, packet, field_name)
      setattr(packet, field_name, '')
