import blocks
from fragments import Fragments

try:
    import cPickle as pickle
except ImportError:
    import pickle

import copy, time, collections
import traceback, sys

Layer = collections.namedtuple('Layer', ['pkt', 'offset'])

class PacketClassBuilder(object):
    def __init__(self, metacls, name, bases, attrs):
        self.metacls = metacls
        self.name = name
        self.bases = bases
        self.attrs = attrs

    def make_configuration(self):
        self.bisturi_conf = self.attrs.get('__bisturi__', {})

    def collect_the_fields(self):
      from field import Field
      self.fields = filter(lambda name_val: isinstance(name_val[1], Field), self.attrs.iteritems())
      self.fields.sort(key=lambda name_val: name_val[1].ctime)

    def make_field_descriptions(self):
      self.fields = sum([valfield.describe_yourself(namefield, self.bisturi_conf) for namefield, valfield in self.fields], [])

    def compile_fields_and_create_slots(self):
      # compile each field (speed optimization) and create the slots (memory optimization)
      additional_slots = self.bisturi_conf.get('additional_slots', [])
      self.slots = sum(map(lambda position, name_val: name_val[1].compile(name_val[0], position, self.fields, self.bisturi_conf), *zip(*enumerate(self.fields))), additional_slots)

    def unroll_fields_with_their_pack_unpack_methods(self):
      # unroll the fields into the their pack/unpack methods (to avoid lookups)
      self.fields = [(name_val[0], name_val[1], name_val[1].pack, name_val[1].unpack) for name_val in self.fields]
      
    def remove_fields_from_class_definition(self):
      for n, _, _, _ in self.fields:
         if n in self.attrs: # check this, because 'describe_yourself' can add new fields
            del self.attrs[n]

    def create_class(self):
      self.attrs['__slots__'] = self.slots
      self.attrs['__bisturi__'] = self.bisturi_conf
      
      self.cls = type.__new__(self.metacls, self.name, self.bases, self.attrs)

    def add_get_fields_class_method(self):
      @classmethod
      def get_fields(cls):
         return self.fields

      self.cls.get_fields = get_fields

    def check_if_we_are_in_debug_mode(self):
      from field import Bkpt
      self.am_in_debug_mode = any((isinstance(field, Bkpt) for _, field, _, _ in self.fields))

    def create_optimized_code(self):
      # create code to optimize the pack/unpack
      # by default, if we are in debug mode, disable the optimization
      generate_by_default = True if not self.am_in_debug_mode else False
      generate_for_pack = self.cls.__bisturi__.get('generate_for_pack', generate_by_default)
      generate_for_unpack = self.cls.__bisturi__.get('generate_for_unpack', generate_by_default)
      write_py_module = self.cls.__bisturi__.get('write_py_module', False)
      blocks.generate_code([(i, name_f[0], name_f[1]) for i, name_f in enumerate(self.fields)], self.cls, generate_for_pack, generate_for_unpack, write_py_module)

    def create_prototype(self):
      pkt = self.cls()
      prototype = Prototype(pkt)
      self.cls.__bisturi__['clone_default_instance_func'] = prototype.clone

    def get_packet_class(self):
      return self.cls

class MetaPacket(type):
   def __new__(metacls, name, bases, attrs):
      if name == 'Packet' and bases == (object,):
         attrs['__slots__'] = []
         return type.__new__(metacls, name, bases, attrs) # Packet base class
 
      builder = PacketClassBuilder(metacls, name, bases, attrs)
    
      builder.make_configuration()

      builder.collect_the_fields()
      builder.make_field_descriptions()
      builder.compile_fields_and_create_slots()
      builder.unroll_fields_with_their_pack_unpack_methods()
      builder.remove_fields_from_class_definition()

      builder.create_class()
      builder.add_get_fields_class_method()

      builder.check_if_we_are_in_debug_mode()

      builder.create_optimized_code()
      builder.create_prototype()
      
      cls = builder.get_packet_class()
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


class PacketError(Exception):
    def __init__(self, was_error_found_in_unpacking_phase, field_name, packet_class_name, offset, original_error_message):
        Exception.__init__(self, "asasasa")
        self.original_traceback = "".join(traceback.format_exception(*sys.exc_info())[2:])

        self.was_error_found_in_unpacking_phase = was_error_found_in_unpacking_phase
        self.fields_stack = [(offset, field_name, packet_class_name)]
        self.original_error_message = original_error_message

    def add_parent_field_and_packet(self, offset, field_name, packet_class_name):
        self.fields_stack.append((offset, field_name, packet_class_name))

    def __str__(self):
        phase = "unpacking" if self.was_error_found_in_unpacking_phase else "packing"
        
        stack_details = "\n".join(["    %08x %s %16s%s" % (offset, packet_class_name, ".", field_name) 
                                    for offset, field_name, packet_class_name in reversed(self.fields_stack)])

        closer_field_offset, closer_field_name, closer_packet_class_name = self.fields_stack[0]
        msg = "Error when %s the field '%s' of packet %s at %08x: %s\nPacket stack details: \n%s\nField's exception:\n%s" % (
                                 phase, 
                                 closer_field_name, closer_packet_class_name,
                                 closer_field_offset,
                                 self.original_error_message,
                                 stack_details,
                                 self.original_traceback)

        return msg


class Packet(object):
   __metaclass__ = MetaPacket
   __bisturi__ = {}


   def __init__(self, bytestring=None, **defaults):
      map(lambda name_val: name_val[1].init(self, defaults), self.__class__.get_fields())
      
      if bytestring is not None:
         self.unpack(bytestring)

   @classmethod
   def build_default_instance(cls):
      return cls.__bisturi__['clone_default_instance_func']()

   def as_prototype(self):
      return Prototype(self)


   def unpack(self, raw, offset=0):
      stack = []
      try:
         return self.unpack_impl(raw, offset, stack)
      except PacketError, e:
         raise e


   def unpack_impl(self, raw, offset, stack):
      stack.append(Layer(self, offset))
      try:
         for name, f, _, unpack in self.get_fields():
            offset = unpack(pkt=self, raw=raw, offset=offset, stack=stack)
      except PacketError, e:
         e.add_parent_field_and_packet(offset, name, self.__class__.__name__)
         raise
      except Exception, e:
         raise PacketError(True, name, self.__class__.__name__, offset, str(e))
      
      stack.pop()
      return offset

   def pack(self):
      fragments = Fragments()
      stack = []
      try:
         return self.pack_impl(fragments, stack)
      except PacketError, e:
         raise e
         

   def pack_impl(self, fragments, stack):
      stack.append(Layer(self, fragments.current_offset))

      try:
         for name, f, pack, _ in self.get_fields():
            pack(pkt=self, fragments=fragments, stack=stack)
      except PacketError, e:
         e.add_parent_field_and_packet(fragments.current_offset, name, self.__class__.__name__)
         raise
      except Exception, e:
         raise PacketError(False, name, self.__class__.__name__, fragments.current_offset, str(e))
      
      stack.pop()
      return fragments

   def iterative_unpack(self, raw, offset=0, stack=None):
      raise NotImplementedError()
      for name, f, _, _ in self.get_fields():
         yield offset, name
         offset = f.unpack(pkt=self, raw=raw, offset=offset, stack=stack)

      yield offset, "."

class Prototype(object):
    def __init__(self, pkt):
       try:
           self.template = pickle.dumps(pkt, -1)
           pickle.loads(self.template) # sanity check
           self.clone = self._clone_from_pickle
       except Exception as e:
           self.template = copy.deepcopy(pkt)
           self.clone = self._clone_from_live_obj

    def clone(self):
       raise Exception()

    def _clone_from_pickle(self):
       return pickle.loads(self.template)

    def _clone_from_live_obj(self):
       return copy.deepcopy(self.template)
