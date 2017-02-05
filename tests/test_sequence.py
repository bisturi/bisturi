import sys, operator
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int, Ref, Bkpt

import unittest
   
class SubPacket(Packet):
   value = Int(1)

class Duple(Packet):
   value = Ref(SubPacket).repeated(count=2)

class TestSequence(unittest.TestCase):
   def _test_sequences_fields(self, obj_one, obj_two,
                                    one_default_raw,     obj_one_defaults, 
                                    two_default_raw,     obj_two_defaults, 
                                    first_raw_for_one,   obj_one_first_values,
                                    second_raw_for_one,  obj_one_second_values, 
                                    second_raw_for_two,  obj_two_second_values,
                                    
                                    remain_of_first_raw_for_one = '',
                                    remain_of_second_raw_for_one = '',
                                    remain_of_second_raw_for_two = ''):

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
         assert str(one_packed) + remain_of_first_raw_for_one == raw
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
         assert str(one_packed) + remain_of_second_raw_for_one == raw  
         assert str(two_packed) + remain_of_second_raw_for_two == raw2


      except Exception, _e:
         import pprint, sys
         _message = _e.message + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e), type(_e)(_message), sys.exc_info()[2]

   def _test_sequences_packet(self, obj_one, obj_two,
                                    one_default_raw,     obj_one_defaults, 
                                    two_default_raw,     obj_two_defaults, 
                                    first_raw_for_one,   obj_one_first_values,
                                    second_raw_for_one,  obj_one_second_values, 
                                    second_raw_for_two,  obj_two_second_values,
                                    
                                    remain_of_first_raw_for_one = '',
                                    remain_of_second_raw_for_one = '',
                                    remain_of_second_raw_for_two = ''):
   
      getval = operator.attrgetter('value')
      try:
         #import pdb; pdb.set_trace()
         one = obj_one
         two = obj_two

         # check defaults
         one_first, one_second = map(getval, one.first), map(getval, one.second)
         two_first, two_second = map(getval, two.first), map(getval, two.second)
         assert (one_first, one_second) == obj_one_defaults
         assert (two_first, two_second) == obj_two_defaults
         
         # check packed defaults
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == one_default_raw
         assert two_packed == two_default_raw

         raw = first_raw_for_one
         one = one.__class__.unpack(raw)
         
         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = map(getval, one.first), map(getval, one.second)
         two_first, two_second = map(getval, two.first), map(getval, two.second)
         assert (one_first, one_second) == obj_one_first_values
         assert (two_first, two_second) == obj_two_defaults
         
         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert str(one_packed) + remain_of_first_raw_for_one == raw 
         assert two_packed == two_default_raw

         raw  = second_raw_for_one
         raw2 = second_raw_for_two
         one = one.__class__.unpack(raw)
         two = two.__class__.unpack(raw2)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = map(getval, one.first), map(getval, one.second)
         two_first, two_second = map(getval, two.first), map(getval, two.second)
         assert (one_first, one_second) == obj_one_second_values
         assert (two_first, two_second) == obj_two_second_values
         
         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert str(one_packed) + remain_of_second_raw_for_one == raw
         assert str(two_packed) + remain_of_second_raw_for_two == raw2


      except Exception, _e:
         import pprint, sys
         _message = _e.message + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e), type(_e)(_message), sys.exc_info()[2]


   def _test_sequences_packet_nested(self, obj_one, obj_two,
                                           one_default_raw,     obj_one_defaults, 
                                           two_default_raw,     obj_two_defaults, 
                                           first_raw_for_one,   obj_one_first_values,
                                           second_raw_for_one,  obj_one_second_values, 
                                           second_raw_for_two,  obj_two_second_values):
   
      getval = operator.attrgetter('value')
      getvals = lambda obj: map(getval, obj.value)
      try:
         #import pdb; pdb.set_trace()
         one = obj_one
         two = obj_two

         # check defaults
         one_first, one_second = map(getvals, one.first), map(getvals, one.second)
         two_first, two_second = map(getvals, two.first), map(getvals, two.second)
         assert (one_first, one_second) == obj_one_defaults
         assert (two_first, two_second) == obj_two_defaults
         
         # check packed defaults
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == one_default_raw
         assert two_packed == two_default_raw

         raw = first_raw_for_one
         one = one.__class__.unpack(raw)
         
         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = map(getvals, one.first), map(getvals, one.second)
         two_first, two_second = map(getvals, two.first), map(getvals, two.second)
         assert (one_first, one_second) == obj_one_first_values
         assert (two_first, two_second) == obj_two_defaults
         
         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == raw 
         assert two_packed == two_default_raw

         raw  = second_raw_for_one
         raw2 = second_raw_for_two
         one = one.__class__.unpack(raw)
         two = two.__class__.unpack(raw2)

         # check parsing (each instance must have its own set of fields and values)
         one_first, one_second = map(getvals, one.first), map(getvals, one.second)
         two_first, two_second = map(getvals, two.first), map(getvals, two.second)
         assert (one_first, one_second) == obj_one_second_values
         assert (two_first, two_second) == obj_two_second_values
         
         # check packing the parsed data
         one_packed, two_packed = one.pack(), two.pack()
         assert one_packed == raw
         assert two_packed == raw2


      except Exception, _e:
         import pprint, sys
         _message = _e.message + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e), type(_e)(_message), sys.exc_info()[2]

   
   def test_field_repeated_fixed_times(self):
      class FieldRepeatedFixedTimes(Packet):
         first  = Int(1).repeated(count=4)
         second = Int(1).repeated(count=4)

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )

   def test_field_repeated_fixed_times_from_field(self):
      class FieldRepeatedFixedTimes(Packet):
         amount = Int(1)
         first  = Int(1).repeated(count=amount)
         second = Int(1).repeated(count=amount)

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '\x00',
         two_default_raw = '\x00',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x04\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x02\x09\x0a\x0b\x0c', 
         second_raw_for_two = '\x03\x0d\x0e\x0f\x10\x11\x12', 
         obj_one_second_values = ([9,  10], [11, 12]), 
         obj_two_second_values = ([13, 14, 15], [16, 17, 18])
      )
   
   def test_field_repeated_fixed_times_from_field_arith_expression(self):
      class FieldRepeatedFixedTimes(Packet):
         param  = Int(1)
         first  = Int(1).repeated(count=param*2)
         second = Int(1).repeated(count=param*3)

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '\x00',
         two_default_raw = '\x00',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x02\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8, 9, 10]),
         second_raw_for_one = '\x01\x0b\x0c\x0d\x0e\x0f', 
         second_raw_for_two = '\x03\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e', 
         obj_one_second_values = ([11, 12], [13, 14, 15]), 
         obj_two_second_values = ([16, 17, 18, 19, 20, 21], [22, 23, 24, 25, 26, 27, 28, 29, 30])
      )
   
   def test_field_repeated_fixed_times_from_field_cmp_expression(self):
      class FieldRepeatedFixedTimes(Packet):
         param  = Int(1)
         first  = Int(1).repeated(count=param > 1) # 1 if param > 1; else 0
         second = Int(1).repeated(count=param > 3) # 1 if param > 3; else 0

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '\x00',
         two_default_raw = '\x00',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x02\x01',   
         obj_one_first_values = ([1], []),
         second_raw_for_one = '\x01', 
         second_raw_for_two = '\x04\x02\x03', 
         obj_one_second_values = ([], []), 
         obj_two_second_values = ([2], [3])
      )
   
   def test_field_repeated_fixed_times_from_field_logical_expression(self):
      class FieldRepeatedFixedTimes(Packet):
         param  = Int(1)
         first  = Int(1).repeated(count=param & 0b0011) # count % 4
         second = Int(1).repeated(count=param & 0b0001) # count % 2

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '\x00',
         two_default_raw = '\x00',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x02\x01\x02',   
         obj_one_first_values = ([1, 2], []),
         second_raw_for_one = '\x01\x03\x04', 
         second_raw_for_two = '\x03\x05\x06\x07\x08', 
         obj_one_second_values = ([3], [4]), 
         obj_two_second_values = ([5, 6, 7], [8])
      )
   
   def test_field_repeated_fixed_times_from_field_logical_expression2(self):
      class FieldRepeatedFixedTimes(Packet):
         param  = Int(1)
         first  = Int(1).repeated(count=(~param & 0xff))
         second = Int(1).repeated(count=(~param & 0xff))

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(),
         one_default_raw = '\x00',
         two_default_raw = '\x00',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\xfe\x01\x02',   
         obj_one_first_values = ([1], [2]),
         second_raw_for_one = '\xfd\x03\x04\x05\x06', 
         second_raw_for_two = '\xfc\x07\x08\x09\x0a\x0b\x0c', 
         obj_one_second_values = ([3, 4], [5, 6]), 
         obj_two_second_values = ([7, 8, 9], [10, 11, 12])
      )


   def test_subpacket_ref_repeated_fixed_times(self):
      class SubpacketRepeatedFixedTimes(Packet):
         first  = Ref(SubPacket).repeated(count=4)
         second = Ref(SubPacket).repeated(count=4)
      
      self._test_sequences_packet(
         obj_one = SubpacketRepeatedFixedTimes(), 
         obj_two = SubpacketRepeatedFixedTimes(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )

   def test_variable_ref_repeated_fixed_times(self):
      class VariableRefRepeatedFixedTimes(Packet):
         first  = Ref(lambda **k: Int(1), default=0).repeated(count=4)
         second = Ref(lambda **k: Int(1), default=0).repeated(count=4)

      self._test_sequences_fields(
         obj_one = VariableRefRepeatedFixedTimes(), 
         obj_two = VariableRefRepeatedFixedTimes(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )

   def XXX_test_variable_ref_changing_repeated_fixed_times(self): # TODO fix this
      class VariableRefRepeatedFixedTimes(Packet):
         first  = Ref(lambda offset, **k: Int(offset%3 + 1), default=0).repeated(count=4)
         second = Ref(lambda offset, **k: Int(offset%3 + 1), default=0).repeated(count=4)

      self._test_sequences_fields(
         obj_one = VariableRefRepeatedFixedTimes(), 
         obj_two = VariableRefRepeatedFixedTimes(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =   '\x01\x00\x02\x03\x00\x04\x05\x00\x06\x07\x00\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x00\x0a\x0b\x00\x0c\x0d\x00\x0e\x0f\x00\x10', 
         second_raw_for_two = '\x11\x00\x12\x13\x00\x14\x15\x00\x16\x17\x00\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )

   def test_field_sequence_until_condition(self):
      class FieldSequenceUntil(Packet):
         first  = Int(1).repeated(until=lambda offset, **k: offset >= 4)
         second = Int(1).repeated(until=lambda offset, **k: offset >= 8)
   
      self._test_sequences_fields(
         obj_one = FieldSequenceUntil(), 
         obj_two = FieldSequenceUntil(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )

   def test_subpacket_sequence_until_condition(self):
      class SubpacketSequenceUntil(Packet):
         first  = Ref(SubPacket).repeated(until=lambda offset, **k: offset >= 4)
         second = Ref(SubPacket).repeated(until=lambda offset, **k: offset >= 8)
   
      self._test_sequences_packet(
         obj_one = SubpacketSequenceUntil(), 
         obj_two = SubpacketSequenceUntil(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )
   
   def test_variable_item_sequence_until_condition(self):
      class VariableItemSequenceUntil(Packet):
         first  = Ref(lambda **k: Int(1), default=0).repeated(until=lambda offset, **k: offset >= 4)
         second = Ref(lambda **k: Int(1), default=0).repeated(until=lambda offset, **k: offset >= 8)
   
      self._test_sequences_fields(
         obj_one = VariableItemSequenceUntil(), 
         obj_two = VariableItemSequenceUntil(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )
   
   def test_field_sequence_until_and_when_condition(self):
      class FieldSequenceUntilAndWhen(Packet):
         first  = Int(1).repeated(until=lambda offset, **k: offset >= 4,
                                  when =lambda raw, offset, **k: raw[offset] != '\xff')
         second = Int(1).repeated(until=lambda offset, **k: offset >= 8,
                                  when =lambda raw, offset, **k: raw[offset] != '\xee')
   
      self._test_sequences_fields(
         obj_one = FieldSequenceUntilAndWhen(), 
         obj_two = FieldSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )
      
      self._test_sequences_fields(
         obj_one = FieldSequenceUntilAndWhen(), 
         obj_two = FieldSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\xff\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([], [0xff, 2, 3, 4, 5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\xee', 
         second_raw_for_two = '\xff\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9, 10, 11, 12], []), 
         obj_two_second_values = ([], [0xff, 18, 19, 20, 21, 22, 23, 24]),
         remain_of_second_raw_for_one = '\xee'
      )
   
   def test_subpacket_sequence_until_and_when_condition(self):
      class SubpacketSequenceUntilAndWhen(Packet):
         first  = Ref(SubPacket).repeated(until=lambda offset, **k: offset >= 4,
                                          when =lambda raw, offset, **k: raw[offset] != '\xff')
         second = Ref(SubPacket).repeated(until=lambda offset, **k: offset >= 8,
                                          when =lambda raw, offset, **k: raw[offset] != '\xee')
   
      self._test_sequences_packet(
         obj_one = SubpacketSequenceUntilAndWhen(), 
         obj_two = SubpacketSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )
      
      self._test_sequences_packet(
         obj_one = SubpacketSequenceUntilAndWhen(), 
         obj_two = SubpacketSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\xff\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([], [0xff, 2, 3, 4, 5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\xee', 
         second_raw_for_two = '\xff\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9, 10, 11, 12], []), 
         obj_two_second_values = ([], [0xff, 18, 19, 20, 21, 22, 23, 24]),
         remain_of_second_raw_for_one = '\xee'
      )
   
   def test_variable_item_sequence_until_and_when_condition(self):
      class VariableItemSequenceUntilAndWhen(Packet):
         first  = Ref(lambda **k: Int(1), default=0).repeated(
                                             until=lambda offset, **k: offset >= 4,
                                             when =lambda raw, offset, **k: raw[offset] != '\xff')
         second = Ref(lambda **k: Int(1), default=0).repeated(
                                             until=lambda offset, **k: offset >= 8,
                                             when =lambda raw, offset, **k: raw[offset] != '\xee')
   
      self._test_sequences_fields(
         obj_one = VariableItemSequenceUntilAndWhen(), 
         obj_two = VariableItemSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([1, 2, 3, 4], [5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9,  10, 11, 12], [13, 14, 15, 16]), 
         obj_two_second_values = ([17, 18, 19, 20], [21, 22, 23, 24])
      )
      
      self._test_sequences_fields(
         obj_one = VariableItemSequenceUntilAndWhen(), 
         obj_two = VariableItemSequenceUntilAndWhen(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\xff\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([], [0xff, 2, 3, 4, 5, 6, 7, 8]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\xee', 
         second_raw_for_two = '\xff\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([9, 10, 11, 12], []), 
         obj_two_second_values = ([], [0xff, 18, 19, 20, 21, 22, 23, 24]),
         remain_of_second_raw_for_one = '\xee'
      )
   
   def test_field_repeated_nested(self):
      class FieldRepeatedNested(Packet):
         first  = Ref(Duple).repeated(count=2)
         second = Ref(Duple).repeated(count=2)

      self._test_sequences_packet_nested(
         obj_one = FieldRepeatedNested(), 
         obj_two = FieldRepeatedNested(),
         one_default_raw = '',
         two_default_raw = '',
         obj_one_defaults = ([], []),
         obj_two_defaults = ([], []),
         first_raw_for_one =  '\x01\x02\x03\x04\x05\x06\x07\x08',   
         obj_one_first_values = ([[1, 2], [3, 4]], [[5, 6], [7, 8]]),
         second_raw_for_one = '\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10', 
         second_raw_for_two = '\x11\x12\x13\x14\x15\x16\x17\x18', 
         obj_one_second_values = ([[9,  10], [11, 12]], [[13, 14], [15, 16]]), 
         obj_two_second_values = ([[17, 18], [19, 20]], [[21, 22], [23, 24]])
      )

   def test_field_repeated_fixed_times_with_defaults(self):
      class FieldRepeatedFixedTimes(Packet):
         first  = Int(1).repeated(count=4, default=[1, 2, 3, 4])
         second = Int(1).repeated(count=4, default=[5, 6, 7, 8])

      self._test_sequences_fields(
         obj_one = FieldRepeatedFixedTimes(), 
         obj_two = FieldRepeatedFixedTimes(second=[9, 10, 11, 12]),
         one_default_raw = '\x01\x02\x03\x04\x05\x06\x07\x08',
         two_default_raw = '\x01\x02\x03\x04\x09\x0a\x0b\x0c',
         obj_one_defaults = ([1, 2, 3, 4], [5, 6, 7, 8]),
         obj_two_defaults = ([1, 2, 3, 4], [9, 10, 11, 12]),
         first_raw_for_one =  '\x0d\x0e\x0f\x10\x11\x12\x13\x14',   
         obj_one_first_values = ([13, 14, 15, 16], [17, 18, 19, 20]),
         second_raw_for_one = '\x15\x16\x17\x18\x19\x1a\x1b\x1c', 
         second_raw_for_two = '\x1d\x1e\x1f\x20\x21\x22\x23\x24',   
         obj_one_second_values = ([21, 22, 23, 24], [25, 26, 27, 28]), 
         obj_two_second_values = ([29, 30, 31, 32], [33, 34, 35, 36])
      )


   def test_field_ref_repeated_fixed_times_with_defaults(self):
      class FieldRefRepeatedFixedTimes(Packet):
         first  = Ref(lambda **k: Int(1), default=0).repeated(count=4, default=[1, 2, 3, 4])
         second = Ref(lambda **k: Int(1), default=0).repeated(count=4, default=[5, 6, 7, 8])

      self._test_sequences_fields(
         obj_one = FieldRefRepeatedFixedTimes(), 
         obj_two = FieldRefRepeatedFixedTimes(second=[9, 10, 11, 12]),
         one_default_raw = '\x01\x02\x03\x04\x05\x06\x07\x08',
         two_default_raw = '\x01\x02\x03\x04\x09\x0a\x0b\x0c',
         obj_one_defaults = ([1, 2, 3, 4], [5, 6, 7, 8]),
         obj_two_defaults = ([1, 2, 3, 4], [9, 10, 11, 12]),
         first_raw_for_one =  '\x0d\x0e\x0f\x10\x11\x12\x13\x14',   
         obj_one_first_values = ([13, 14, 15, 16], [17, 18, 19, 20]),
         second_raw_for_one = '\x15\x16\x17\x18\x19\x1a\x1b\x1c', 
         second_raw_for_two = '\x1d\x1e\x1f\x20\x21\x22\x23\x24',   
         obj_one_second_values = ([21, 22, 23, 24], [25, 26, 27, 28]), 
         obj_two_second_values = ([29, 30, 31, 32], [33, 34, 35, 36])
      )
   

   def test_subpacket_ref_repeated_fixed_times_with_defaults(self):
      class SubpacketRepeatedFixedTimes(Packet):
         first  = Ref(SubPacket).repeated(count=4, default=[
                                                      SubPacket(value=1),
                                                      SubPacket(value=2),
                                                      SubPacket(value=3),
                                                      SubPacket(value=4)  ])
         second = Ref(SubPacket).repeated(count=4, default=[
                                                      SubPacket(value=5),
                                                      SubPacket(value=6),
                                                      SubPacket(value=7),
                                                      SubPacket(value=8)  ])

      self._test_sequences_packet(
         obj_one = SubpacketRepeatedFixedTimes(), 
         obj_two = SubpacketRepeatedFixedTimes(second=[
                                                      SubPacket(value=9),
                                                      SubPacket(value=10),
                                                      SubPacket(value=11),
                                                      SubPacket(value=12)  ]),
         one_default_raw = '\x01\x02\x03\x04\x05\x06\x07\x08',
         two_default_raw = '\x01\x02\x03\x04\x09\x0a\x0b\x0c',
         obj_one_defaults = ([1, 2, 3, 4], [5, 6, 7, 8]),
         obj_two_defaults = ([1, 2, 3, 4], [9, 10, 11, 12]),
         first_raw_for_one =  '\x0d\x0e\x0f\x10\x11\x12\x13\x14',   
         obj_one_first_values = ([13, 14, 15, 16], [17, 18, 19, 20]),
         second_raw_for_one = '\x15\x16\x17\x18\x19\x1a\x1b\x1c', 
         second_raw_for_two = '\x1d\x1e\x1f\x20\x21\x22\x23\x24',   
         obj_one_second_values = ([21, 22, 23, 24], [25, 26, 27, 28]), 
         obj_two_second_values = ([29, 30, 31, 32], [33, 34, 35, 36])
      )

   def test_variable_ref_repeated_fixed_times_with_defaults(self):
      class VariableRefRepeatedFixedTimes(Packet):
         first  = Ref(lambda **k: Int(1), default=0).repeated(count=4, default=[1, 2, 3, 4])
         second = Ref(lambda **k: Int(1), default=0).repeated(count=4, default=[5, 6, 7, 8])

      self._test_sequences_fields(
         obj_one = VariableRefRepeatedFixedTimes(), 
         obj_two = VariableRefRepeatedFixedTimes(second=[9, 10, 11, 12]),
         one_default_raw = '\x01\x02\x03\x04\x05\x06\x07\x08',
         two_default_raw = '\x01\x02\x03\x04\x09\x0a\x0b\x0c',
         obj_one_defaults = ([1, 2, 3, 4], [5, 6, 7, 8]),
         obj_two_defaults = ([1, 2, 3, 4], [9, 10, 11, 12]),
         first_raw_for_one =  '\x0d\x0e\x0f\x10\x11\x12\x13\x14',   
         obj_one_first_values = ([13, 14, 15, 16], [17, 18, 19, 20]),
         second_raw_for_one = '\x15\x16\x17\x18\x19\x1a\x1b\x1c', 
         second_raw_for_two = '\x1d\x1e\x1f\x20\x21\x22\x23\x24',   
         obj_one_second_values = ([21, 22, 23, 24], [25, 26, 27, 28]), 
         obj_two_second_values = ([29, 30, 31, 32], [33, 34, 35, 36])
      )
'''
class B(Packet):
   first  = Int(1).repeated(count=1)
   second = Int(1).repeated(count=0)
   


class A(Packet):

'''
