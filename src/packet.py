from field import Field
import re


class MetaPacket(type):
   def __init__(cls, name, bases, attrs):
      type.__init__(cls, name, bases, attrs)

      if name == 'Packet' and bases == (object,):
         return # Packet base class
   
      fields = filter(lambda name_val: isinstance(name_val[1], Field), attrs.iteritems())
      fields.sort(key=lambda name_val: name_val[1].ctime)
      
      map(lambda name_val: name_val[1].compile(name_val[0]), fields)

      @classmethod
      def get_fields(cls):
         return fields

      cls.get_fields = get_fields

class Packet(object):
   __metaclass__ = MetaPacket

   END = re.compile('$')

   def __init__(self, bytestring=None, **defaults):
      map(lambda name_val: name_val[1].init(self, defaults), self.get_fields())
      
      if bytestring is not None:
         self.from_raw(bytestring)


   def from_raw(self, raw, offset=0):
      for name, f in self.get_fields():
         offset += f.from_raw(self, raw[offset:])

      return offset
         
   def to_raw(self):
      return ''.join([f.to_raw(self) for name, f in self.get_fields()])

