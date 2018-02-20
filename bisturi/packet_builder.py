from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
import bisturi.blocks
import copy, pprint

from bisturi.six import integer_types

__trace_enabled = False
__trace_indent = 0
def _trace(pargs=[], pattrs=[], presult=False):
    def decorator(method):
        def wrapper(self, *args, **kargs):
            global __trace_indent

            who = getattr(self, '__name__', self.__class__.__name__)
            indent = " " * __trace_indent
            print("{i}{who} {method}".format(i=indent, who=who,
                                             method=method.__name__))

            if pargs:
                print("{i}Args:".format(i=indent))
                for p in pargs:
                    try:
                        val = args[p]
                    except:
                        val = kargs[p]

                    print("{i}{arg}: {val}".format(i=indent, arg=p,
                                                    val=pprint.pformat(val)))

            __trace_indent += 1
            try:
                result = method(self, *args, **kargs)
            finally:
                __trace_indent -= 1

            if pattrs:
                print("{i}Attrs post-call:".format(i=indent))
                for p in pattrs:
                    val = getattr(self, p)
                    print("{i}{arg}: {val}".format(i=indent, arg=p,
                                                    val=pprint.pformat(val)))

            if presult:
                print("{i}Result: {val}".format(i=indent,
                                                    val=pprint.pformat(val)))

            return result

        if __trace_enabled:
            return wrapper
        else:
            return method
    return decorator

class PacketClassBuilder(object):
    def __init__(self, metacls, name, bases, attrs):
        self.metacls = metacls
        self.name = name
        self.bases = bases
        self.attrs = attrs

    def bisturi_configuration_default(self):
        return {}

    @_trace(pattrs=['bisturi_conf'])
    def make_configuration(self):
        defaults = self.bisturi_configuration_default()
        self.bisturi_conf = self.attrs.get('__bisturi__', defaults)

    def create_field_name_from_subpacket_name(self, subpacket_name):
        '''Helper method to transform names like CamelCase into camel_case'''
        name = subpacket_name[0].lower() + subpacket_name[1:]
        return "".join((c if c.islower() else "_"+c.lower()) for c in name)

    @_trace(pattrs=['attrs'])
    def create_fields_for_embebed_subclasses_and_replace_them(self):
        ''' Create Ref fields to refer to 'embebed' subclasses.
            Something like this:

            class A(Packet):
                class B(Packet):
                    pass

            is transformed into

            class A(Packet):
                b = Ref(B)

            See the method create_field_name_from_subpacket_name to know how
            the name 'B' was transformed into 'b'.
        '''

        from bisturi.packet import Packet
        from bisturi.field import Ref
        import inspect

        def is_a_packet_instance(name_and_field):
            _, field = name_and_field
            return inspect.isclass(field) and issubclass(field, Packet)

        names_and_subpackets = filter(is_a_packet_instance, self.attrs.items())
        subpackets_as_refs = [(self.create_field_name_from_subpacket_name(name),
                               Ref(prototype=subpacket, _is_a_subpacket_definition=True)) \
                                    for name, subpacket in names_and_subpackets]

        self.attrs.update(dict(subpackets_as_refs))

    @_trace(pattrs=['fields_in_class', 'original_fields_in_class'])
    def collect_the_fields_from_class_definition(self):
        ''' Collect the fields of the packet and sort them by creation time.
            Take something like this:

            class A(Packet):
                a = 1
                b = Int(2)
                c = Int(2)

            and collect [b->Int(2), c->Int(2)]
        '''
        from bisturi.field import Field

        def is_a_field_instance(name_and_field):
            _, field = name_and_field
            return isinstance(field, Field)

        def creation_time_of_field(name_and_field):
            _, field = name_and_field
            return field.ctime

        self.fields_in_class = filter(is_a_field_instance, self.attrs.items())
        self.fields_in_class = sorted(self.fields_in_class,
                                        key=creation_time_of_field)

        self.original_fields_in_class = list(self.fields_in_class)

    @_trace(pattrs=['fields'])
    def ask_to_each_field_to_describe_itself(self):
        ''' Ask to each field to describe itself. This should return for each
            field a list of names and fields which represent that original field.
            In most cases one field is described by only one field (itself) but
            there are cases where multiple field are needed.

            class A(Packet):
                a = Int(1)
                b = Int(2).at(0)

            The orignal list of fields should be [a->Int(1), b->Int(2)]
            but after the description of both fields we have a new list of fields:
                [a->Int(1), _shift_b_->Move(0), b->Int(2)]

            How each field is describe will depend of each field instance.
            See the method _describe_yourself of each Field subclass.
        '''
        self.fields = sum([field._describe_yourself(name, self.bisturi_conf) \
                            for name, field in self.fields_in_class], [])

    @_trace(pattrs=['slots'])
    def compile_fields_and_create_slots(self):
        ''' Compile each field, allowing them to optimize their pack/unpack
            methods.
            Also collect them and create the necessary slots to optimize the
            memory usage, then extend the slot list with the slots given by
            the user.
        '''

        def compile_field(position, name_and_field):
            _, field = name_and_field
            return field._compile(position, self.fields, self.bisturi_conf)

        additional_slots = self.bisturi_conf.get('additional_slots', [])
        self.slots = sum(map(compile_field, *zip(*enumerate(self.fields))), additional_slots)

    @_trace(pattrs=['slots'])
    def compile_descriptors_and_extend_slots(self):
        ''' Compile each field's descriptor if any and add their slots to the
            slot list.
        '''
        def has_descriptor(field):
            return field.descriptor is not None and hasattr(field.descriptor, '_compile')

        self.slots += sum((field.descriptor._compile(name, field.descriptor_name, self.bisturi_conf) for name, field in self.fields
               if has_descriptor(field)), [])


    @_trace()
    def lookup_pack_unpack_methods(self):
        ''' The list of fields is transformed in a list of tuples with the
            pack/unpack methods of each field ready to be called avoiding a
            further lookup.

            Take this [a->Int(1), b->Int(2)] into
                [(a, Int(1), a.pack, a.unpack),
                 (b, Int(2), b.pack, b.unpack),
                 ]
        '''
        self.fields = [(name, field, field.pack, field.unpack) for name, field in self.fields]

    @_trace(pattrs=['attrs'])
    def remove_fields_from_class_definition(self):
        ''' Remove from the class definition any field.
            Take this:
                class A(Packet):
                    a = 1
                    b = Int(2)

            and transform it into:
                class A(Packet):
                    a = 1
        '''
        for name, _ in self.original_fields_in_class:
            del self.attrs[name]

    @_trace(pattrs=['attrs', 'slots'])
    def add_descriptors_to_class_definition(self):
        ''' Add to the class definition any field's descriptor.
            It will replace a field by its descriptor.
            Take this:
                class A(Packet):
                    a = 1
                    b = Int(2).describe(Foo)

            and transform it into:
                class A(Packet):
                    a = 1
                    b = Foo()
        '''
        for name, field in self.fields:
            if field.descriptor:
                self.attrs[field.descriptor_name] = field.descriptor
                self.slots.remove(field.descriptor_name)

    @_trace()
    def collect_sync_methods_from_field_descriptors(self):
        self.sync_before_pack_methods = []
        self.sync_after_unpack_methods = []
        for name, field in self.fields:
            if field.descriptor:
                try:
                    self.sync_before_pack_methods.append(field.descriptor.sync_before_pack)
                except AttributeError:
                    pass

                try:
                    self.sync_after_unpack_methods.append(field.descriptor.sync_after_unpack)
                except AttributeError:
                    pass

    @_trace(pattrs=['metacls', 'name', 'bases', 'attrs', 'cls'])
    def create_class(self):
        ''' Create the class with the correct attributes and slots.
            If it is necessary, the original attributes (fields) can be access
            via the dictionary __bisturi__, key original_fields_in_class.
        '''
        self.bisturi_conf['original_fields_in_class'] = self.original_fields_in_class

        self.attrs['__slots__'] = self.slots
        self.attrs['__bisturi__'] = self.bisturi_conf

        self.cls = type.__new__(self.metacls, self.name, self.bases, self.attrs)

    @_trace()
    def add_get_fields_class_method(self):
        @classmethod
        def get_fields(cls):
            return self.fields

        self.cls.get_fields = get_fields

    @_trace()
    def add_sync_descriptor_class_methods(self):
        @classmethod
        def get_sync_before_pack_methods(cls):
            return self.sync_before_pack_methods

        @classmethod
        def get_sync_after_unpack_methods(cls):
            return self.sync_after_unpack_methods

        self.cls.get_sync_before_pack_methods = get_sync_before_pack_methods
        self.cls.get_sync_after_unpack_methods = get_sync_after_unpack_methods

    @_trace(pattrs=['am_in_debug_mode'])
    def check_if_we_are_in_debug_mode(self):
        ''' A class creation is in debug mode if one of its fields is
            a breakpoint (Bkpt).
        '''
        from bisturi.field import Bkpt
        self.am_in_debug_mode = any((isinstance(field, Bkpt) for _, field in self.fields))

    @_trace()
    def create_optimized_code(self):
        ''' Generate the optimized code for the pack and unpack methods and
            replace the original version for the optimized ones.

            The generation can be disabled is partially with the configuration
            flagos generate_for_pack/generate_for_unpack.
            And it is totally disabled if the class is in debug mode
            (see check_if_we_are_in_debug_mode)

            Optinally the generated code can be kept to manual inspection
            with the flag write_py_module in True.
        '''
        generate_by_default = True if not self.am_in_debug_mode else False

        generate_for_pack = self.cls.__bisturi__.get('generate_for_pack', generate_by_default)
        generate_for_unpack = self.cls.__bisturi__.get('generate_for_unpack', generate_by_default)

        write_py_module = self.cls.__bisturi__.get('write_py_module', False)

        bisturi.blocks.generate_code([(i, name_f[0], name_f[1]) for i, name_f in enumerate(self.fields)], self.cls, generate_for_pack, generate_for_unpack, write_py_module)

    @_trace()
    def get_packet_class(self):
        return self.cls

    @_trace()
    def create_collect_and_describe_the_field_list(self):
        ''' Given a class definition create any extra field necessary,
            then collect all of them and at last ask to each field to
            describe itself returning a final list of fields.
        '''
        self.create_fields_for_embebed_subclasses_and_replace_them()
        self.collect_the_fields_from_class_definition()
        self.ask_to_each_field_to_describe_itself()

    @_trace()
    def compile_fields_and_descriptors_and_create_slots(self):
        ''' Each field and each descriptor is compiled, optimized and
            added to the list of slots.
        '''
        self.compile_fields_and_create_slots()
        self.compile_descriptors_and_extend_slots()

    @_trace()
    def create_packet_class_and_add_its_special_methods(self):
        self.create_class()
        self.add_get_fields_class_method()
        self.add_sync_descriptor_class_methods()

    @_trace()
    def remove_fields_from_and_add_descriptors_to_class_definition(self):
        self.remove_fields_from_class_definition()
        self.add_descriptors_to_class_definition()

    @_trace()
    def optimize_methods(self):
        self.check_if_we_are_in_debug_mode()
        self.lookup_pack_unpack_methods()
        self.create_optimized_code()

class PacketSpecializationClassBuilder(PacketClassBuilder):
    def __init__(self, metacls, name, bases, attrs):
        from bisturi.packet import Packet

        self.super_class = attrs['__bisturi__']['specialization_of']
        assert isinstance(self.super_class, Packet)

        original_fields_in_superclass = self.super_class.__bisturi__['original_fields_in_class']
        specialized_fields = self.specialize_fields(attrs, original_fields_in_superclass)

        PacketClassBuilder.__init__(self, metacls, name, bases, specialized_attrs)

    def bisturi_configuration_default(self):
        return copy.deepcopy(self.super_class.__bisturi__)

    def specialize_fields(self, specialization_attrs, original_fields_in_superclass):
        specialized_fields = copy.deepcopy(original_fields_in_superclass)
        for attrname, attrvalue in specialization_attrs:
            if isinstance(attrvalue, Field) and attrname not in original_fields_in_superclass:
                raise Exception("You cannot add new fields like '%s'." % attrname)

            if isinstance(attrvalue, integer_types + (bytes, )) and attrname in original_fields_in_superclass:
                specialized_fields[attrname].default = attrvalue  # TODO the default or a constant??

            if isinstance(attrvalue, Field) and attrname in original_fields_in_superclass:
                attrvalue.ctime = original_fields_in_superclass[attrname].ctime # override the creation time to keep the same order
                specialized_fields[attrname] = attrvalue

        return specialized_fields

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

        builder.create_collect_and_describe_the_field_list()
        builder.compile_fields_and_descriptors_and_create_slots()

        builder.collect_sync_methods_from_field_descriptors()

        builder.remove_fields_from_and_add_descriptors_to_class_definition()
        builder.create_packet_class_and_add_its_special_methods()

        builder.optimize_methods()

        cls = builder.get_packet_class()
        return cls

