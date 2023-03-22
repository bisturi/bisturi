import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Ref, Int

import unittest

class SubPacket(Packet):
   value = Int(1)

class TestRef(unittest.TestCase):
   def _test_refs_field(self,
                                # the objects under test
                                obj_one, obj_two,

                                # the expected default values
                                #  - the raw (packed) value
                                #  - the python object values (int, strings...)
                                one_default_raw,     obj_one_defaults,
                                two_default_raw,     obj_two_defaults,

                                # unpack the given raw item "xx_raw_for_xx"
                                # for the given object (one or two)
                                # and compare the unpacked values with the
                                # expected ones
                                first_raw_for_one,   obj_one_first_values,
                                second_raw_for_one,  obj_one_second_values,
                                second_raw_for_two,  obj_two_second_values,

                                # pack the objects and check that the raw
                                # string are equal to the raw before plus
                                # these remains
                                remain_of_first_raw_for_one = b'',
                                remain_of_second_raw_for_one = b'',
                                remain_of_second_raw_for_two = b''):

      try:
         #import pdb; pdb.set_trace()
         one = obj_one
         two = obj_two

         # check defaults
         one_first, one_second = one.first, one.second
         two_first, two_second = two.first, two.second
         assert (one_first, one_second) == obj_one_defaults
         assert (two_first, two_second) == obj_two_defaults

         # check packed defaults
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == one_default_raw
         assert two_packed == two_default_raw

         raw = first_raw_for_one
         one = one.__class__.unpack(raw)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = one.first, one.second
         two_first, two_second = two.first, two.second
         assert (one_first, one_second) == obj_one_first_values
         assert (two_first, two_second) == obj_two_defaults

         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed + remain_of_first_raw_for_one == raw
         assert two_packed == two_default_raw

         raw  = second_raw_for_one
         raw2 = second_raw_for_two
         one = one.__class__.unpack(raw)
         two = two.__class__.unpack(raw2)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = one.first, one.second
         two_first, two_second = two.first, two.second
         assert (one_first, one_second) == obj_one_second_values
         assert (two_first, two_second) == obj_two_second_values

         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed + remain_of_second_raw_for_one == raw
         assert two_packed + remain_of_second_raw_for_two == raw2

      except Exception as _e:
         import pprint, sys, traceback
         _message = str(_e) + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e)(_message + '\n' + traceback.format_exc())

   def _test_refs_packet(self,
                                # the objects under test
                                obj_one, obj_two,

                                # the expected default values
                                #  - the raw (packed) value
                                #  - the python object values (int, strings...)
                                one_default_raw,     obj_one_defaults,
                                two_default_raw,     obj_two_defaults,

                                # unpack the given raw item "xx_raw_for_xx"
                                # for the given object (one or two)
                                # and compare the unpacked values with the
                                # expected ones
                                first_raw_for_one,   obj_one_first_values,
                                second_raw_for_one,  obj_one_second_values,
                                second_raw_for_two,  obj_two_second_values,

                                # pack the objects and check that the raw
                                # string are equal to the raw before plus
                                # these remains
                                remain_of_first_raw_for_one = b'',
                                remain_of_second_raw_for_one = b'',
                                remain_of_second_raw_for_two = b''):

      try:
         #import pdb; pdb.set_trace()
         one = obj_one
         two = obj_two

         # check defaults
         one_first, one_second = one.first.value, one.second.value
         two_first, two_second = two.first.value, two.second.value
         assert (one_first, one_second) == obj_one_defaults
         assert (two_first, two_second) == obj_two_defaults

         # check packed defaults
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == one_default_raw
         assert two_packed == two_default_raw

         raw = first_raw_for_one
         one = one.__class__.unpack(raw)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = one.first.value, one.second.value
         two_first, two_second = two.first.value, two.second.value
         assert (one_first, one_second) == obj_one_first_values
         assert (two_first, two_second) == obj_two_defaults

         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed + remain_of_first_raw_for_one == raw
         assert two_packed == two_default_raw

         raw  = second_raw_for_one
         raw2 = second_raw_for_two
         one = one.__class__.unpack(raw)
         two = two.__class__.unpack(raw2)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = one.first.value, one.second.value
         two_first, two_second = two.first.value, two.second.value
         assert (one_first, one_second) == obj_one_second_values
         assert (two_first, two_second) == obj_two_second_values

         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed + remain_of_second_raw_for_one == raw
         assert two_packed + remain_of_second_raw_for_two == raw2

      except Exception as _e:
         import pprint, sys, traceback
         _message = str(_e) + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e)(_message + '\n' + traceback.format_exc())


   def test_ref_subpacket(self):
      class RefSubPacket(Packet):
         first  = Ref(SubPacket)
         second = Ref(SubPacket)

      self._test_refs_packet(
         obj_one = RefSubPacket(),
         obj_two = RefSubPacket(),
         one_default_raw = b'\x00\x00',
         two_default_raw = b'\x00\x00',
         obj_one_defaults = (0, 0),
         obj_two_defaults = (0, 0),
         first_raw_for_one =  b'\x01\x02',
         obj_one_first_values = (1, 2),
         second_raw_for_one = b'\x03\x04',
         second_raw_for_two = b'\x05\x06',
         obj_one_second_values = (3, 4),
         obj_two_second_values = (5, 6)
      )

   def test_ref_subpacket_using_an_instance(self):
      class RefSubPacketWithInstance(Packet):
         first  = Ref(SubPacket(value=1))
         second = Ref(SubPacket(value=2))

      self._test_refs_packet(
         obj_one = RefSubPacketWithInstance(),
         obj_two = RefSubPacketWithInstance(),
         one_default_raw = b'\x01\x02',
         two_default_raw = b'\x01\x02',
         obj_one_defaults = (1, 2),
         obj_two_defaults = (1, 2),
         first_raw_for_one =  b'\x03\x04',
         obj_one_first_values = (3, 4),
         second_raw_for_one = b'\x05\x06',
         second_raw_for_two = b'\x07\x08',
         obj_one_second_values = (5, 6),
         obj_two_second_values = (7, 8)
      )

   def test_ref_variable_int_field(self):
      class RefVariableIntField(Packet):
         first  = Ref(lambda **k: Int(1),  default=1)
         second = Ref(lambda **k: Int(4),  default=2)

      self._test_refs_field(
         obj_one = RefVariableIntField(),
         obj_two = RefVariableIntField(),
         one_default_raw = b'\x01\x00\x00\x00\x02',
         two_default_raw = b'\x01\x00\x00\x00\x02',
         obj_one_defaults = (1, 2),
         obj_two_defaults = (1, 2),
         first_raw_for_one =  b'\x03\x00\x00\x00\x04',
         obj_one_first_values = (3, 4),
         second_raw_for_one = b'\x05\x00\x00\x00\x06',
         second_raw_for_two = b'\x07\x00\x00\x00\x08',
         obj_one_second_values = (5, 6),
         obj_two_second_values = (7, 8)
      )

   def test_ref_variable_subpacket(self):
      class RefVariableSubPacket(Packet):
         first  = Ref(lambda **k: SubPacket(value=1),  default=SubPacket(value=2))
         second = Ref(lambda **k: SubPacket(value=3),  default=SubPacket(value=4))

      self._test_refs_packet(
         obj_one = RefVariableSubPacket(),
         obj_two = RefVariableSubPacket(),
         one_default_raw = b'\x02\x04',
         two_default_raw = b'\x02\x04',
         obj_one_defaults = (2, 4),
         obj_two_defaults = (2, 4),
         first_raw_for_one =  b'\x03\x05',
         obj_one_first_values = (3, 5),
         second_raw_for_one = b'\x06\x07',
         second_raw_for_two = b'\x08\x09',
         obj_one_second_values = (6, 7),
         obj_two_second_values = (8, 9)
      )


   def test_ref_int_field_defaults_from_user(self):
      class RefIntField(Packet):
         first  = Ref(lambda **k: Int(4),  default=8)
         second = Ref(lambda **k: Int(4),  default=16)

      self._test_refs_field(
         obj_one = RefIntField(first=1),
         obj_two = RefIntField(first=2, second=3),
         one_default_raw = b'\x00\x00\x00\x01\x00\x00\x00\x10',
         two_default_raw = b'\x00\x00\x00\x02\x00\x00\x00\x03',
         obj_one_defaults = (1, 16),
         obj_two_defaults = (2, 3),
         first_raw_for_one =  b'\x00\x00\x00\x04\x00\x00\x00\x05',
         obj_one_first_values = (4, 5),
         second_raw_for_one = b'\x00\x00\x00\x06\x00\x00\x00\x07',
         second_raw_for_two = b'\x00\x00\x00\x08\x00\x00\x00\x09',
         obj_one_second_values = (6, 7),
         obj_two_second_values = (8, 9)
      )


   def test_ref_subpacket_defaults_from_user(self):
      class RefSubPacket(Packet):
         first  = Ref(SubPacket)
         second = Ref(SubPacket(value=1))

      self._test_refs_packet(
         obj_one = RefSubPacket(first=SubPacket(value=2)),
         obj_two = RefSubPacket(first=SubPacket(value=3), second=SubPacket(value=4)),
         one_default_raw = b'\x02\x01',
         two_default_raw = b'\x03\x04',
         obj_one_defaults = (2, 1),
         obj_two_defaults = (3, 4),
         first_raw_for_one =  b'\x05\x06',
         obj_one_first_values = (5, 6),
         second_raw_for_one = b'\x07\x08',
         second_raw_for_two = b'\x09\x0a',
         obj_one_second_values = (7, 8),
         obj_two_second_values = (9, 0xa)
      )

   def test_ref_variable_int_field_defaults_from_user(self):
      class RefVariableIntField(Packet):
         first  = Ref(lambda **k: Int(1),  default=1)
         second = Ref(lambda **k: Int(4),  default=2)

      self._test_refs_field(
         obj_one = RefVariableIntField(first=3),
         obj_two = RefVariableIntField(first=4, second=5),
         one_default_raw = b'\x03\x00\x00\x00\x02',
         two_default_raw = b'\x04\x00\x00\x00\x05',
         obj_one_defaults = (3, 2),
         obj_two_defaults = (4, 5),
         first_raw_for_one =  b'\x06\x00\x00\x00\x07',
         obj_one_first_values = (6, 7),
         second_raw_for_one = b'\x08\x00\x00\x00\x09',
         second_raw_for_two = b'\x0a\x00\x00\x00\x0b',
         obj_one_second_values = (8, 9),
         obj_two_second_values = (0xa, 0xb)
      )

   def test_ref_variable_subpacket_defaults_from_user(self):
      class RefVariableSubPacket(Packet):
         first  = Ref(lambda **k: SubPacket(value=1),  default=SubPacket(value=2))
         second = Ref(lambda **k: SubPacket(value=3),  default=SubPacket(value=4))

      self._test_refs_packet(
         obj_one = RefVariableSubPacket(first=SubPacket(value=5)),
         obj_two = RefVariableSubPacket(first=SubPacket(value=6), second=SubPacket(value=7)),
         one_default_raw = b'\x05\x04',
         two_default_raw = b'\x06\x07',
         obj_one_defaults = (5, 4),
         obj_two_defaults = (6, 7),
         first_raw_for_one =  b'\x08\x09',
         obj_one_first_values = (8, 9),
         second_raw_for_one = b'\x0a\x0b',
         second_raw_for_two = b'\x0c\x0d',
         obj_one_second_values = (0xa, 0xb),
         obj_two_second_values = (0xc, 0xd)
      )


   def test_ref_variable_callback_parameter(self):
      arguments_per_call = []
      def get_prototype(**k):
         arguments_per_call.append(k)
         return Int(2)

      class RefVariableCorrectParameters(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Ref(get_prototype, default=0)
         second = Ref(get_prototype, default=0)

      one = RefVariableCorrectParameters()

      assert len(arguments_per_call) == 0 # no called

      raw = b'\x00\x00\x00\x01'
      one = one.__class__.unpack(raw)
      assert len(arguments_per_call) == 2
      first_call, second_call = arguments_per_call

      assert first_call == {
            'pkt': one,
            'raw': raw,
            'offset': 0,
            'local_offset': 0,
            'root': one,
         }

      assert second_call == {
            'pkt': one,
            'raw': raw,
            'offset': 2,
            'local_offset': 0,
            'root': one,
         }

      arguments_per_call.pop()   # cleanup
      arguments_per_call.pop()

      # TODO add more tests on packing
