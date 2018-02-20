from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from bisturi.fragments import Fragments, FragmentsOfRegexps
from bisturi.pattern_matching import Any

try:
    import cPickle as pickle
except ImportError:
    import pickle

import copy, collections
import traceback, sys, re

import bisturi.packet_builder

from bisturi.six import with_metaclass

class PacketError(Exception):
    def __init__(self, was_error_found_in_unpacking_phase, field_name, packet_class_name, offset, original_error_message):
        Exception.__init__(self, "")
        self.original_traceback = "".join(traceback.format_exception(*sys.exc_info())[2:])

        self.was_error_found_in_unpacking_phase = was_error_found_in_unpacking_phase
        self.fields_stack = [(offset, field_name, packet_class_name)]
        self.original_error_message = original_error_message

    def add_parent_field_and_packet(self, offset, field_name, packet_class_name):
        self.fields_stack.append((offset, field_name, packet_class_name))

    def __str__(self):
        phase = "unpacking" if self.was_error_found_in_unpacking_phase else "packing"

        stack_details = []
        for offset, field_name, packet_class_name in reversed(self.fields_stack):
            offset_and_pkt_class = "    %08x %s" % (offset, packet_class_name)
            first_part_len = len(offset_and_pkt_class)

            space = " " * max(44 - first_part_len, 1)

            line = "%s%s.%s" % (offset_and_pkt_class, space, field_name)
            stack_details.append(line)

        stack_details = "\n".join(stack_details)

        closer_field_offset, closer_field_name, closer_packet_class_name = self.fields_stack[0]
        msg = "Error when %s the field '%s' of packet %s at %08x: %s\nPacket stack details: \n%s\nField's exception:\n%s" % (
                                 phase,
                                 closer_field_name, closer_packet_class_name,
                                 closer_field_offset,
                                 self.original_error_message,
                                 stack_details,
                                 self.original_traceback)

        return msg

class Packet(with_metaclass(bisturi.packet_builder.MetaPacket, object)):
    __bisturi__ = {}

    def __init__(self, _initialize_fields=True, **defaults):
        assert _initialize_fields in (True, False)
        if _initialize_fields:
            for field_name, field, _, _ in self.__class__.get_fields():
                field.init(self, defaults)
                try:
                    descriptor_name = field.descriptor_name
                    default_value = defaults[descriptor_name]
                    setattr(self, descriptor_name, default_value)
                except AttributeError:
                    pass
                except KeyError:
                    pass

    def as_prototype(self):
        return Prototype(self)

    @classmethod
    def unpack(cls, raw, offset=0, silent=False):
        if not isinstance(raw, bytes):
            raise ValueError("The raw parameter must be 'bytes', not '%s'." % type(raw))

        pkt = cls(_initialize_fields=False)
        try:
            pkt.unpack_impl(raw, offset, root=pkt)
            return pkt
        except PacketError as e:
            e.packet = pkt
            if silent:
                return None
            else:
                raise e
        except:
            if silent:
                return None
            else:
                raise


    def unpack_impl(self, raw, offset, **k):
        k['local_offset'] = offset
        try:
            for name, f, _, unpack in self.get_fields():
                offset = unpack(pkt=self, raw=raw, offset=offset, **k)
        except PacketError as e:
            e.add_parent_field_and_packet(offset, name, self.__class__.__name__)
            raise
        except Exception as e:
            raise PacketError(True, name, self.__class__.__name__, offset, str(e))

        [sync(self) for sync in self.get_sync_after_unpack_methods()]
        return offset

    def pack(self):
        fragments = Fragments()
        try:
            fragments = self.pack_impl(fragments, root=self)
            return fragments.tobytes()
        except PacketError as e:
            e.packet = self
            raise e


    def pack_impl(self, fragments, **k):
        [sync(self) for sync in self.get_sync_before_pack_methods()]
        k['local_offset'] = fragments.current_offset

        try:
            for name, f, pack, _ in self.get_fields():
                pack(pkt=self, fragments=fragments, **k)
        except PacketError as e:
            e.add_parent_field_and_packet(fragments.current_offset, name, self.__class__.__name__)
            raise
        except Exception as e:
            raise PacketError(False, name, self.__class__.__name__, fragments.current_offset, str(e))

        return fragments

    def as_regular_expression(self, debug=False):
        fragments = FragmentsOfRegexps()
        stack = []
        self.as_regular_expression_impl(fragments, stack)

        return re.compile(b"(?s)" + fragments.assemble_regexp(), re.DEBUG if debug else 0)


    def as_regular_expression_impl(self, fragments, stack):
        for name, f, pack, _ in self.get_fields():
            f.pack_regexp(self, fragments, stack=stack)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        for name, f, pack, _ in self.get_fields():
            if getattr(self, name) != getattr(other, name):
                return False

        return True


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

