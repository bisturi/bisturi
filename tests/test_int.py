from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int

import unittest

class TestInt(unittest.TestCase):
   def _test_ints(self, obj_one, obj_two,
                        one_default_raw,     obj_one_defaults, 
                        two_default_raw,     obj_two_defaults, 
                        first_raw_for_one,   obj_one_first_values,
                        second_raw_for_one,  obj_one_second_values, 
                        second_raw_for_two,  obj_two_second_values):

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
         assert one_packed == raw 
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
         assert one_packed == raw 
         assert two_packed == raw2


      except Exception, _e:
         import pprint, sys
         _message = _e.message + '\n' + pprint.pformat(dict(filter(lambda k_v: not k_v[0].startswith("__"), locals().items())))
         raise type(_e), type(_e)(_message), sys.exc_info()[2]


   def test_double_int(self):
      class Double(Packet):
         first  = Int(4)
         second = Int(4)
    
      self._test_ints(
         obj_one = Double(), 
         obj_two = Double(),
         one_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x00',
         obj_one_defaults = (0, 0), 
         obj_two_defaults = (0, 0), 
         first_raw_for_one =   '\x00\x00\x00\x01\x00\x00\x00\x02',   
         obj_one_first_values = (1, 2),
         second_raw_for_one =  '\x00\x00\x00\x03\x00\x00\x00\x04', 
         second_raw_for_two = '\x00\x00\x00\x05\x00\x00\x00\x06', 
         obj_one_second_values = (3, 4), 
         obj_two_second_values = (5, 6)
      )

   def test_double_int_with_distinct_defaults(self):
      class WithDefaults(Packet):
         first  = Int(4, default=1)
         second = Int(4, default=2)
      
      self._test_ints(
         obj_one = WithDefaults(), 
         obj_two = WithDefaults(),
         one_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x02',
         two_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x00\x00\x00\x03\x00\x00\x00\x04',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x00\x00\x00\x05\x00\x00\x00\x06', 
         second_raw_for_two = '\x00\x00\x00\x07\x00\x00\x00\x08', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )

   def test_double_int_with_signs(self):
      class MinusOneSigned(Packet):
         first  = Int(2, signed=True,  default=-1)
         second = Int(2, signed=False, default=1)
         
      self._test_ints(
         obj_one = MinusOneSigned(), 
         obj_two = MinusOneSigned(),
         one_default_raw = '\xff\xff\x00\x01',
         two_default_raw = '\xff\xff\x00\x01',
         obj_one_defaults = (-1, 1), 
         obj_two_defaults = (-1, 1), 
         first_raw_for_one =   '\xff\xfe\x00\x02',   
         obj_one_first_values = (-2, 2),
         second_raw_for_one =  '\x80\x02\x00\x03', 
         second_raw_for_two = '\x80\x04\x00\x05', 
         obj_one_second_values = (-32766, 3), 
         obj_two_second_values = (-32764, 5)
      )

   def test_double_int_with_endian(self):
      class ChangedEndianess(Packet):
         first  = Int(4, endianness='little',  default=1)
         second = Int(4, endianness='little',  default=2)
         
      self._test_ints(
         obj_one = ChangedEndianess(), 
         obj_two = ChangedEndianess(),
         one_default_raw = '\x01\x00\x00\x00\x02\x00\x00\x00',
         two_default_raw = '\x01\x00\x00\x00\x02\x00\x00\x00',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x03\x00\x00\x00\x04\x00\x00\x00',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x05\x00\x00\x00\x06\x00\x00\x00', 
         second_raw_for_two = '\x07\x00\x00\x00\x08\x00\x00\x00', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )


   def test_rare_int_with_distinct_defaults(self):
      class RareSizeWithDefaults(Packet):
         first  = Int(3, default=1)
         second = Int(3, default=2)
      
      self._test_ints(
         obj_one = RareSizeWithDefaults(), 
         obj_two = RareSizeWithDefaults(),
         one_default_raw = '\x00\x00\x01\x00\x00\x02',
         two_default_raw = '\x00\x00\x01\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x00\x00\x03\x00\x00\x04',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x00\x00\x05\x00\x00\x06', 
         second_raw_for_two = '\x00\x00\x07\x00\x00\x08', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )

   def test_rare_int_with_signs(self):
      class RareSizeMinusOneSigned(Packet):
         first  = Int(3, signed=True,  default=-1)
         second = Int(3, signed=False, default=1)
      
      self._test_ints(
         obj_one = RareSizeMinusOneSigned(), 
         obj_two = RareSizeMinusOneSigned(),
         one_default_raw = '\xff\xff\xff\x00\x00\x01',
         two_default_raw = '\xff\xff\xff\x00\x00\x01',
         obj_one_defaults = (-1, 1), 
         obj_two_defaults = (-1, 1), 
         first_raw_for_one =   '\xff\xff\xfe\x00\x00\x02',   
         obj_one_first_values = (-2, 2),
         second_raw_for_one =  '\x80\x00\x02\x00\x00\x03', 
         second_raw_for_two = '\x80\x00\x04\x00\x00\x05', 
         obj_one_second_values = (-8388606, 3), 
         obj_two_second_values = (-8388604, 5)
      )

   def test_rare_int_with_endian(self):
      class RareSizeMinusOneChangedEndianess(Packet):
         first  = Int(3, endianness='little',  default=1)
         second = Int(3, endianness='little',  default=2)
         
      self._test_ints(
         obj_one = RareSizeMinusOneChangedEndianess(), 
         obj_two = RareSizeMinusOneChangedEndianess(),
         one_default_raw = '\x01\x00\x00\x02\x00\x00',
         two_default_raw = '\x01\x00\x00\x02\x00\x00',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x03\x00\x00\x04\x00\x00',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x05\x00\x00\x06\x00\x00', 
         second_raw_for_two = '\x07\x00\x00\x08\x00\x00', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )

   def test_double_int_defaults_from_user(self):
      class Double(Packet):
         first  = Int(4)
         second = Int(4)
    
      self._test_ints(
         obj_one = Double(first=1), 
         obj_two = Double(second=2),
         one_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x02',
         obj_one_defaults = (1, 0), 
         obj_two_defaults = (0, 2), 
         first_raw_for_one =   '\x00\x00\x00\x03\x00\x00\x00\x02',   
         obj_one_first_values = (3, 2),
         second_raw_for_one =  '\x00\x00\x00\x04\x00\x00\x00\x05', 
         second_raw_for_two = '\x00\x00\x00\x06\x00\x00\x00\x07', 
         obj_one_second_values = (4, 5), 
         obj_two_second_values = (6, 7)
      )

   def test_rare_int_defaults_from_user(self):
      class Double(Packet):
         first  = Int(3)
         second = Int(3)
    
      self._test_ints(
         obj_one = Double(first=1), 
         obj_two = Double(second=2),
         one_default_raw = '\x00\x00\x01\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x02',
         obj_one_defaults = (1, 0), 
         obj_two_defaults = (0, 2), 
         first_raw_for_one =   '\x00\x00\x03\x00\x00\x02',   
         obj_one_first_values = (3, 2),
         second_raw_for_one =  '\x00\x00\x04\x00\x00\x05', 
         second_raw_for_two = '\x00\x00\x06\x00\x00\x07', 
         obj_one_second_values = (4, 5), 
         obj_two_second_values = (6, 7)
      )

   def test_double_int_without_optimizations(self):
      class Double(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Int(4)
         second = Int(4)
    
      self._test_ints(
         obj_one = Double(), 
         obj_two = Double(),
         one_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x00',
         obj_one_defaults = (0, 0), 
         obj_two_defaults = (0, 0), 
         first_raw_for_one =   '\x00\x00\x00\x01\x00\x00\x00\x02',   
         obj_one_first_values = (1, 2),
         second_raw_for_one =  '\x00\x00\x00\x03\x00\x00\x00\x04', 
         second_raw_for_two = '\x00\x00\x00\x05\x00\x00\x00\x06', 
         obj_one_second_values = (3, 4), 
         obj_two_second_values = (5, 6)
      )

   def test_double_int_with_distinct_defaults(self):
      class WithDefaults(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Int(4, default=1)
         second = Int(4, default=2)
      
      self._test_ints(
         obj_one = WithDefaults(), 
         obj_two = WithDefaults(),
         one_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x02',
         two_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x00\x00\x00\x03\x00\x00\x00\x04',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x00\x00\x00\x05\x00\x00\x00\x06', 
         second_raw_for_two = '\x00\x00\x00\x07\x00\x00\x00\x08', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )


   def test_rare_int_with_distinct_defaults(self):
      class RareSizeWithDefaults(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Int(3, default=1)
         second = Int(3, default=2)
      
      self._test_ints(
         obj_one = RareSizeWithDefaults(), 
         obj_two = RareSizeWithDefaults(),
         one_default_raw = '\x00\x00\x01\x00\x00\x02',
         two_default_raw = '\x00\x00\x01\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw_for_one =   '\x00\x00\x03\x00\x00\x04',   
         obj_one_first_values = (3, 4),
         second_raw_for_one =  '\x00\x00\x05\x00\x00\x06', 
         second_raw_for_two = '\x00\x00\x07\x00\x00\x08', 
         obj_one_second_values = (5, 6), 
         obj_two_second_values = (7, 8)
      )
   
   def test_double_int_defaults_from_user_without_optimizations(self):
      class Double(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Int(4)
         second = Int(4)
    
      self._test_ints(
         obj_one = Double(first=1), 
         obj_two = Double(second=2),
         one_default_raw = '\x00\x00\x00\x01\x00\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x00\x00\x02',
         obj_one_defaults = (1, 0), 
         obj_two_defaults = (0, 2), 
         first_raw_for_one =   '\x00\x00\x00\x03\x00\x00\x00\x02',   
         obj_one_first_values = (3, 2),
         second_raw_for_one =  '\x00\x00\x00\x04\x00\x00\x00\x05', 
         second_raw_for_two = '\x00\x00\x00\x06\x00\x00\x00\x07', 
         obj_one_second_values = (4, 5), 
         obj_two_second_values = (6, 7)
      )

   def test_rare_int_defaults_from_user_without_optimizations(self):
      class Double(Packet):
         __bisturi__ = {'generate_for_pack': False, 'generate_for_unpack': False}
         first  = Int(3)
         second = Int(3)
    
      self._test_ints(
         obj_one = Double(first=1), 
         obj_two = Double(second=2),
         one_default_raw = '\x00\x00\x01\x00\x00\x00',
         two_default_raw = '\x00\x00\x00\x00\x00\x02',
         obj_one_defaults = (1, 0), 
         obj_two_defaults = (0, 2), 
         first_raw_for_one =   '\x00\x00\x03\x00\x00\x02',   
         obj_one_first_values = (3, 2),
         second_raw_for_one =  '\x00\x00\x04\x00\x00\x05', 
         second_raw_for_two = '\x00\x00\x06\x00\x00\x07', 
         obj_one_second_values = (4, 5), 
         obj_two_second_values = (6, 7)
      )
