import array
from bisturi.packet import Packet 

def inspect(packet, indent=""):
   print "%s%s" % (indent, packet.__class__.__name__)
   print "%s%s" % (indent, "=" * len(packet.__class__.__name__))
   for name, _ in packet.get_fields():
      value = getattr(packet, name)
      if isinstance(value, array.array):
         value = value.tostring()

      if isinstance(value, basestring):
         value = ':'.join(x.encode('hex') for x in value)

      if isinstance(value, Packet):
         print "%s%s:" % (indent, name)
         inspect(value, indent+"  ")
         value = None

      if isinstance(value, (list, tuple)):
         if value:
            print "%s%s: [" % (indent, name)
            for subvalue in value:
               inspect(subvalue, indent+"  ")
            print "%s]" % (indent, )
         else:
            print "%s%s: []" % (indent, name)

         value = None

      if value is not None:
         print "%s%s = %s" % (indent, name, value)

