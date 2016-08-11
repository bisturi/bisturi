import array

def inspect(packet):
   print packet.__class__.__name__
   print "=" * len(packet.__class__.__name__)
   for name, _ in packet.get_fields():
      value = getattr(packet, name)
      if isinstance(value, array.array):
         value = value.tostring()

      if isinstance(value, basestring):
         value = ':'.join(x.encode('hex') for x in value)

      print "%s = %s" % (name, value)

