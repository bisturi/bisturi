import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Int

import unittest

class TestInt(unittest.TestCase):
   def _test_ints(self, obj_one, obj_two,
                        default_raw, obj_one_defaults, obj_two_defaults, 
                        first_raw,   obj_one_values,
                        first_raw2, second_raw2, obj_one_values2, obj_two_values2):

      try:
         #import pdb; pdb.set_trace()
         one = obj_one
         two = obj_two

         # check defaults
         assert (one.first, one.second) == obj_one_defaults
         assert (two.first, two.second) == obj_two_defaults
         assert one.pack() == two.pack() == default_raw

         raw = first_raw
         one.unpack(raw)
         
         # check parsing (each instance must have its own set of fields and values)
         assert (one.first, one.second) == obj_one_values
         assert (two.first, two.second) == obj_two_defaults
         assert one.pack() == raw and two.pack() == default_raw

         raw  = first_raw2
         raw2 = second_raw2
         one.unpack(raw)
         two.unpack(raw2)

         # check parsing (each instance must have its own set of fields and values)
         assert (one.first, one.second) == obj_one_values2
         assert (two.first, two.second) == obj_two_values2
         assert one.pack() == raw and two.pack() == raw2

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
         default_raw = '\x00\x00\x00\x00\x00\x00\x00\x00',
         obj_one_defaults = (0, 0), 
         obj_two_defaults = (0, 0), 
         first_raw =   '\x00\x00\x00\x01\x00\x00\x00\x02',   
         obj_one_values = (1, 2),
         first_raw2 =  '\x00\x00\x00\x03\x00\x00\x00\x04', 
         second_raw2 = '\x00\x00\x00\x05\x00\x00\x00\x06', 
         obj_one_values2 = (3, 4), 
         obj_two_values2 = (5, 6)
      )

   def test_double_int_with_distinct_defaults(self):
      class WithDefaults(Packet):
         first  = Int(4, default=1)
         second = Int(4, default=2)
      
      self._test_ints(
         obj_one = WithDefaults(), 
         obj_two = WithDefaults(),
         default_raw = '\x00\x00\x00\x01\x00\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw =   '\x00\x00\x00\x03\x00\x00\x00\x04',   
         obj_one_values = (3, 4),
         first_raw2 =  '\x00\x00\x00\x05\x00\x00\x00\x06', 
         second_raw2 = '\x00\x00\x00\x07\x00\x00\x00\x08', 
         obj_one_values2 = (5, 6), 
         obj_two_values2 = (7, 8)
      )

   def test_double_int_with_signs(self):
      class MinusOneSigned(Packet):
         first  = Int(2, signed=True,  default=-1)
         second = Int(2, signed=False, default=1)
         
      self._test_ints(
         obj_one = MinusOneSigned(), 
         obj_two = MinusOneSigned(),
         default_raw = '\xff\xff\x00\x01',
         obj_one_defaults = (-1, 1), 
         obj_two_defaults = (-1, 1), 
         first_raw =   '\xff\xfe\x00\x02',   
         obj_one_values = (-2, 2),
         first_raw2 =  '\x80\x02\x00\x03', 
         second_raw2 = '\x80\x04\x00\x05', 
         obj_one_values2 = (-32766, 3), 
         obj_two_values2 = (-32764, 5)
      )

   def test_double_int_with_endian(self):
      class ChangedEndianess(Packet):
         first  = Int(4, endianess='little',  default=1)
         second = Int(4, endianess='little',  default=2)
         
      self._test_ints(
         obj_one = ChangedEndianess(), 
         obj_two = ChangedEndianess(),
         default_raw = '\x01\x00\x00\x00\x02\x00\x00\x00',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw =   '\x03\x00\x00\x00\x04\x00\x00\x00',   
         obj_one_values = (3, 4),
         first_raw2 =  '\x05\x00\x00\x00\x06\x00\x00\x00', 
         second_raw2 = '\x07\x00\x00\x00\x08\x00\x00\x00', 
         obj_one_values2 = (5, 6), 
         obj_two_values2 = (7, 8)
      )


   def test_rare_int_with_distinct_defaults(self):
      class RareSizeWithDefaults(Packet):
         first  = Int(3, default=1)
         second = Int(3, default=2)
      
      self._test_ints(
         obj_one = RareSizeWithDefaults(), 
         obj_two = RareSizeWithDefaults(),
         default_raw = '\x00\x00\x01\x00\x00\x02',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw =   '\x00\x00\x03\x00\x00\x04',   
         obj_one_values = (3, 4),
         first_raw2 =  '\x00\x00\x05\x00\x00\x06', 
         second_raw2 = '\x00\x00\x07\x00\x00\x08', 
         obj_one_values2 = (5, 6), 
         obj_two_values2 = (7, 8)
      )

   def test_rare_int_with_signs(self):
      class RareSizeMinusOneSigned(Packet):
         first  = Int(3, signed=True,  default=-1)
         second = Int(3, signed=False, default=1)
      
      self._test_ints(
         obj_one = RareSizeMinusOneSigned(), 
         obj_two = RareSizeMinusOneSigned(),
         default_raw = '\xff\xff\xff\x00\x00\x01',
         obj_one_defaults = (-1, 1), 
         obj_two_defaults = (-1, 1), 
         first_raw =   '\xff\xff\xfe\x00\x00\x02',   
         obj_one_values = (-2, 2),
         first_raw2 =  '\x80\x00\x02\x00\x00\x03', 
         second_raw2 = '\x80\x00\x04\x00\x00\x05', 
         obj_one_values2 = (-8388606, 3), 
         obj_two_values2 = (-8388604, 5)
      )

   def test_rare_int_with_endian(self):
      class RareSizeMinusOneChangedEndianess(Packet):
         first  = Int(3, endianess='little',  default=1)
         second = Int(3, endianess='little',  default=2)
         
      self._test_ints(
         obj_one = RareSizeMinusOneChangedEndianess(), 
         obj_two = RareSizeMinusOneChangedEndianess(),
         default_raw = '\x01\x00\x00\x02\x00\x00',
         obj_one_defaults = (1, 2), 
         obj_two_defaults = (1, 2), 
         first_raw =   '\x03\x00\x00\x04\x00\x00',   
         obj_one_values = (3, 4),
         first_raw2 =  '\x05\x00\x00\x06\x00\x00', 
         second_raw2 = '\x07\x00\x00\x08\x00\x00', 
         obj_one_values2 = (5, 6), 
         obj_two_values2 = (7, 8)
      )


