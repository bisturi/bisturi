import blocks
from fragments import Fragments

try:
    import cPickle as pickle
except ImportError:
    import pickle

import copy, time

class MetaPacket(type):
   def __new__(metacls, name, bases, attrs):
      if name == 'Packet' and bases == (object,):
         attrs['__slots__'] = []
         return type.__new__(metacls, name, bases, attrs) # Packet base class
 
      # get the configuration, if any
      bisturi_conf = attrs.get('__bisturi__', {})

      # collect the fields (Field)  
      from field import Field
      fields = filter(lambda name_val: isinstance(name_val[1], Field), attrs.iteritems())
      fields.sort(key=lambda name_val: name_val[1].ctime)

      # request to describe yourself to each field
      fields = sum([valfield.describe_yourself(namefield) for namefield, valfield in fields], [])
      
      # compile and create the slots (memory optimization)
      additional_slots = bisturi_conf.get('additional_slots', [])
      slots = sum(map(lambda position, name_val: name_val[1].compile(name_val[0], position, fields, bisturi_conf), *zip(*enumerate(fields))), additional_slots)
      
      # extend the field list with the their pack/unpack methods (to avoid lookups)
      fields = [(name_val[0], name_val[1], name_val[1].pack, name_val[1].unpack) for name_val in fields]
      @classmethod
      def get_fields(cls):
         return fields

      attrs['__slots__'] = slots
      attrs['__bisturi__'] = bisturi_conf
      
      # remove the fields from the class definition
      for n, _, _, _ in fields:
         if n in attrs: # check this, because 'describe_yourself' can add new fields
            del attrs[n]

      cls = type.__new__(metacls, name, bases, attrs)

      cls.get_fields = get_fields
      
      # create code to optimize the pack/unpack
      generate_for_pack = cls.__bisturi__.get('generate_for_pack', True)
      generate_for_unpack = cls.__bisturi__.get('generate_for_unpack', True)
      write_py_module = cls.__bisturi__.get('write_py_module', False)
      blocks.generate_code([(i, name_f[0], name_f[1]) for i, name_f in enumerate(fields)], cls, generate_for_pack, generate_for_unpack, write_py_module)
 

      return cls

   '''def __getattribute__(self, name):
      """ Let be
          class P(Packet):
            f = Field()

          f is a Field, but P.f is a member_descriptor. This happen because
          Packet implements the __slots__ attribute and hides the fields.
          To restore this we need to do this ugly and inefficient lookup."""
      obj = type.__getattribute__(self, name)
      try:
         # try to find the Field if any
         return [f for n, f, _, _ in obj.__objclass__.get_fields() if n == name][0]
      except:
         pass
      return obj'''

class Packet(object):
   __metaclass__ = MetaPacket
   __bisturi__ = {}


   def __init__(self, bytestring=None, **defaults):
      map(lambda name_val: name_val[1].init(self, defaults), self.__class__.get_fields())
      
      if bytestring is not None:
         self.unpack(bytestring)

   @classmethod
   def build_default_instance(cls):
       try:
           obj = cls._build_default_instance_from_picked()
           cls.build_default_instance = cls._build_default_instance_from_picked
       except:
           try:
               obj = cls._build_default_instance_copying()
               cls.build_default_instance = cls._build_default_instance_copying
           except:
               obj = cls()
               cls.__bisturi__['default_instance'] = obj
               
               try:
                   cls.__bisturi__['default_instance_pickled'] = pickle.dumps(obj, -1)
               except:
                   pass

       return obj

   @classmethod
   def _build_default_instance_from_picked(cls):
       return pickle.loads(cls.__bisturi__['default_instance_pickled'])

   @classmethod
   def _build_default_instance_copying(cls):
       return copy.deepcopy(cls.__bisturi__['default_instance'])

   def clone_prototype(self):
       keyword = hash(hash(self) % time.time())
       try:
           obj = pickle.loads(self.__bisturi__['instance_pickled__%s' % keyword])
       except Exception as e:
           try:
               self.__bisturi__['instance_pickled__%s' % keyword] = pickle.dumps(self, -1)
           except Exception as e:
               pass
 
           obj = copy.deepcopy(self)

       return obj

   def unpack(self, raw, offset=0, stack=None):
      stack = self.push_to_the_stack(stack)
      try:
         for name, f, _, unpack in self.get_fields():
            offset = unpack(pkt=self, raw=raw, offset=offset, stack=stack)
      except Exception, e:
         import traceback
         msg = traceback.format_exc()
         raise Exception("Error when parsing field '%s' of packet %s at %08x: %s" % (
                                 name, self.__class__.__name__, offset, msg))
      
      self.pop_from_the_stack(stack)
      return offset
         
   def pack(self, fragments=None, stack=None):
      stack = self.push_to_the_stack(stack)

      if fragments is None:
         fragments = Fragments()

      try:
         for name, f, pack, _ in self.get_fields():
            pack(pkt=self, fragments=fragments, stack=stack)
      except Exception, e:
         import traceback
         msg = traceback.format_exc()
         raise Exception("Error when packing field '%s' of packet %s at %08x: %s" % (
                                 name, self.__class__.__name__, fragments.current_offset, msg))
      
      self.pop_from_the_stack(stack)

      return fragments

   def push_to_the_stack(self, stack):
      if stack:
         stack.append(self)
      else:
         stack = [self]

      return stack

   def pop_from_the_stack(self, stack):
      stack.pop()

   def iterative_unpack(self, raw, offset=0, stack=None):
      stack = self.push_to_the_stack(stack)
      for name, f, _, _ in self.get_fields():
         yield offset, name
         offset = f.unpack(pkt=self, raw=raw, offset=offset, stack=stack)

      yield offset, "."
      
