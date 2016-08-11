import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Ref

class BMP(Packet):
  __bisturi__ = {'endianness': 'little'}

  signature = Data(2, default="BM")

  file_size = Int(4)
  reserved1 = Int(2)
  reserved2 = Int(2)

  offset_pixel_array = Int(4)

class DIB(Packet):
  header_size = Int(4)
   
  image_width  = Int(4)
  image_height = Int(4)

  planes = Int(2)
  bits_per_pixel = Int(2)

  compression = Int(4)
  image_size  = Int(4)

  x_pixels_per_meter = Int(4)
  y_pixels_per_meter = Int(4)
  colors_in_color_table = Int(4)
  important_color_count = Int(4)

  red_channel_bitmask   = Int(4)
  green_channel_bitmask = Int(4)
  blue_channel_bitmask  = Int(4)
  alpha_channel_bitmask = Int(4)

  color_space_type = Int(4)
  color_space_endpoints= Int(4)

  gamma_for_red_channel   = Int(4)
  gamma_for_green_channel = Int(4)
  gamma_for_blue_channel  = Int(4)

  intent = Int(4)
  icc_profile_data = Int(4)
  icc_profile_size = Int(4)

  reserved = Int(4)

