from bisect import insort

class Fragments(object):
   def __init__(self, fill='.'):
      self.fragments = {}
      self.next_offset = 0
      self.fill = fill

   def append(self, string):
      self.insert(self.next_offset, string)

   def extend(self, iterable):
      for string in iterable:
         self.insert(self.next_offset, string)

   def insert(self, position, string):
      if not string:
         return

      if position in self.fragments:
         raise Exception("Collision detected at %08x" % position)

      self.fragments[position] = string
      self.next_offset = position + len(string)

   def __str__(self):
      begin = 0
      result = []
      for offset, s in sorted(self.fragments.iteritems()):
         result.append(self.fill * (offset-begin))
         result.append(s)
         begin = offset + len(s)

      return ''.join(result)

   def __repr__(self):
      return repr(sorted(self.fragments.iteritems()))

   def __eq__(self, other):
      assert isinstance(other, basestring)
      return str(self) == other
