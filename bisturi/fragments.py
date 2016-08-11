from bisect import insort, bisect_left, bisect_right

class Fragments(object):
   def __init__(self, fill='.'):
      self.fragments = {}
      self.begin_of_fragments = []
      self.current_offset = 0
      self.fill = fill

   def append(self, string):
      self.insert(self.current_offset, string)

   def extend(self, iterable):
      for string in iterable:
         self.insert(self.current_offset, string)

   def insert(self, position, string):
      #if not string:
      #   return

      #if position in self.fragments:
      #   raise Exception("Collision detected at %08x" % position)

      i = bisect_right(self.begin_of_fragments, position) - 1
      L = len(string)
      if self.fragments:
         b1 = self.begin_of_fragments[i]
         e1 = b1 + len(self.fragments[b1])
 
         if b1 <= position < e1:
            raise Exception("Collision detected with previous fragment %08x-%08x when inserting new fragment at %08x that span to %08x" % (b1, e1, position, position+L))

         if i+1 < len(self.begin_of_fragments):
            b2 = self.begin_of_fragments[i+1]
            
            if b2 < position + L:
               e2 = b2 + len(self.fragments[b2])
               raise Exception("Collision detected with previous fragment %08x-%08x when inserting new fragment at %08x that span to %08x" % (b2, e2, position, position+L))


      self.begin_of_fragments.insert(i+1, position)

      self.fragments[position] = string
      self.current_offset = position + L

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
