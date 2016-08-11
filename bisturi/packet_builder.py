import blocks
import copy


class PacketClassBuilder(object):
    def __init__(self, metacls, name, bases, attrs):
        self.metacls = metacls
        self.name = name
        self.bases = bases
        self.attrs = attrs
        
    def bisturi_configuration_default(self):
        return {}

    def make_configuration(self):
        self.bisturi_conf = self.attrs.get('__bisturi__', self.bisturi_configuration_default())

    def create_field_name_from_subpacket_name(self, subpacket_name):
        name = subpacket_name[0].lower() + subpacket_name[1:]
        return "".join((c if c.islower() else "_"+c.lower()) for c in name)

    def create_fields_for_embebed_subclasses_and_replace_them(self):
        from packet import Packet
        from field import Ref
        import inspect
        subpackets = filter(lambda name_val: inspect.isclass(name_val[1]) and issubclass(name_val[1], Packet), self.attrs.iteritems())
        subpackets_as_refs = [(self.create_field_name_from_subpacket_name(name), 
                               Ref(prototype=subpacket, _is_a_subpacket_definition=True)) for name, subpacket in subpackets]

        self.attrs.update(dict(subpackets_as_refs))

    def collect_the_fields(self):
      from field import Field
      self.fields_in_class = filter(lambda name_val: isinstance(name_val[1], Field), self.attrs.iteritems())
      self.fields_in_class.sort(key=lambda name_val: name_val[1].ctime)

      self.original_fields_in_class = list(self.fields_in_class)

    def make_field_descriptions(self):
      self.fields = sum([valfield.describe_yourself(namefield, self.bisturi_conf) for namefield, valfield in self.fields_in_class], [])

    def compile_fields_and_create_slots(self):
      # compile each field (speed optimization) and create the slots (memory optimization)
      additional_slots = self.bisturi_conf.get('additional_slots', [])
      self.slots = sum(map(lambda position, name_val: name_val[1].compile(position, self.fields, self.bisturi_conf), *zip(*enumerate(self.fields))), additional_slots)
    
    def compile_descriptors_and_extend_slots(self):
      self.slots += sum((field.descriptor.compile(field_name, field.descriptor_name, self.bisturi_conf) for field_name, field in self.fields
               if field.descriptor is not None and hasattr(field.descriptor, 'compile')), [])


    def unroll_fields_with_their_pack_unpack_methods(self):
      # unroll the fields into the their pack/unpack methods (to avoid lookups)
      self.fields = [(name_val[0], name_val[1], name_val[1].pack, name_val[1].unpack) for name_val in self.fields]
      
    def remove_fields_from_class_definition(self):
      for name, _ in self.original_fields_in_class:
         del self.attrs[name]
    
    def add_descriptors_to_class_definition(self):
      for name, field, _, _ in self.fields:
          if field.descriptor:
              self.attrs[field.descriptor_name] = field.descriptor
    
    def collect_sync_methods_from_field_descriptors(self):
      self.sync_before_pack_methods = [] 
      self.sync_after_unpack_methods = []
      for name, field, _, _ in self.fields:
          if field.descriptor:
              try:
                  self.sync_before_pack_methods.append(field.descriptor.sync_before_pack)
              except AttributeError:
                  pass
              try:
                  self.sync_after_unpack_methods.append(field.descriptor.sync_after_unpack)
              except AttributeError:
                  pass

    def create_class(self):
      self.bisturi_conf['original_fields_in_class'] = self.original_fields_in_class

      self.attrs['__slots__'] = self.slots
      self.attrs['__bisturi__'] = self.bisturi_conf
      
      self.cls = type.__new__(self.metacls, self.name, self.bases, self.attrs)

    def add_get_fields_class_method(self):
      @classmethod
      def get_fields(cls):
         return self.fields

      self.cls.get_fields = get_fields

    def add_sync_descriptor_class_methods(self):
      @classmethod
      def get_sync_before_pack_methods(cls):
         return self.sync_before_pack_methods
      
      @classmethod
      def get_sync_after_unpack_methods(cls):
         return self.sync_after_unpack_methods

      self.cls.get_sync_before_pack_methods = get_sync_before_pack_methods
      self.cls.get_sync_after_unpack_methods = get_sync_after_unpack_methods

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

    def get_packet_class(self):
      return self.cls

class PacketSpecializationClassBuilder(PacketClassBuilder):
    def __init__(self, metacls, name, bases, attrs):
        from packet import Packet

        self.super_class = attrs['__bisturi__']['specialization_of']
        assert isinstance(self.super_class, Packet)

        original_fields_in_class = self.super_class.__bisturi__['original_fields_in_class']
        specialized_fields = self.specialize_fields(attrs, original_fields_in_class)

        PacketClassBuilder.__init__(self, metacls, name, bases, specialized_attrs)

    def bisturi_configuration_default(self):
        return copy.deepcopy(self.super_class.__bisturi__)

    def specialize_fields(self, specialization_attrs, original_fields):
        for attrname, attrvalue in specialization_attrs:
            if isinstance(attrvalue, Field) and attrname not in original_fields:
                raise Exception("You cannot add new fields like '%s'." % attrname)

            if isinstance(attrvalue, (int, long, basestring)) and attrname in original_fields:
                original_fields[attrname].default = attrvalue  # TODO the default or a constant??

            if isinstance(attrvalue, Field) and attrname in original_fields:
                attrvalue.ctime = original_fields[attrname].ctime # override the creation time to keep the same order
                original_fields[attrname] = attrvalue

        return original_fields

class MetaPacket(type):
   def __new__(metacls, name, bases, attrs):
      if name == 'Packet' and bases == (object,):
         attrs['__slots__'] = []
         return type.__new__(metacls, name, bases, attrs) # Packet base class

      specialization_of = attrs.get('__bisturi__', {}).get('specialization_of', None)
      if specialization_of:
          builder = PacketSpecializationClassBuilder(metacls, name, bases, attrs)

      else:
          builder = PacketClassBuilder(metacls, name, bases, attrs)
    
      builder.make_configuration()

      builder.create_fields_for_embebed_subclasses_and_replace_them()

      builder.collect_the_fields()
      builder.make_field_descriptions()
      builder.compile_fields_and_create_slots()
      builder.compile_descriptors_and_extend_slots()

      builder.unroll_fields_with_their_pack_unpack_methods()
      builder.remove_fields_from_class_definition()
      builder.add_descriptors_to_class_definition()
      builder.collect_sync_methods_from_field_descriptors()

      builder.create_class()
      builder.add_get_fields_class_method()
      builder.add_sync_descriptor_class_methods()

      builder.check_if_we_are_in_debug_mode()

      builder.create_optimized_code()
      
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


