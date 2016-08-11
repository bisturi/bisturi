from field import Field


class MetaPacket(type):
   def __init__(cls, name, bases, attrs):
      type.__init__(cls, name, bases, attrs)

      if name == 'Packet' and bases == (object,):
         return # Packet base class
   
      fields = filter(lambda name_val: isinstance(name_val[1], Field), attrs.iteritems())
      fields.sort(key=lambda name_val: name_val[1].ctime)
      
      map(lambda name_val: name_val[1].compile(), fields)

      @classmethod
      def get_fields(cls):
         return fields

      cls.get_fields = get_fields

class Packet(object):
   __metaclass__ = MetaPacket

   def __init__(self, **defaults):
      map(lambda name_val: name_val[1].init(self, name_val[0], defaults), self.get_fields())


   def from_raw(self, raw, offset=0):
      cls = self.__class__
      for name, f in cls.get_fields():
         offset += f.from_raw(raw[offset:])

      return offset
         

