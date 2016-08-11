import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Ref, Em, Bkpt

class DIB(Packet):
  __bisturi__ = {'endianness': 'little'}
  header_size = Int(4)
   
  image_width  = Int(4)
  image_height = Int(4)

  planes = Int(2, default=1)
  bits_per_pixel = Int(2, default=32)

  compression = Int(4)
  image_size  = Int(4)

  x_pixels_per_meter = Int(4)
  y_pixels_per_meter = Int(4)
  colors_in_color_table = Int(4)

  '''
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
  '''

  reserved = Int(4)

class PixelRow(Packet):
  __bisturi__ = {'endianness': 'little'}
  pixels = Int(1).repeated(lambda pkt, stack, **k: stack[0].image_width*3)
  tail = Data(lambda pkt, stack, **k: pkt.pad(stack))

  def pad(self, stack):
     N = stack[0].image_width*3
     return (4 - (N % 4)) % 4

class BMP(Packet):
  __bisturi__ = {'endianness': 'little', 'write_py_module': True}

  signature = Data(2, default="BM")

  file_size = Int(4)
  reserved1 = Int(2)
  reserved2 = Int(2)

  offset_pixel_array = Int(4)

  dib = Ref(DIB, embeb=True)

  pixel_rows = Ref(PixelRow).repeated(lambda pkt, stack, **k: stack[0].image_height)\
                      .at(offset_pixel_array)
  

if __name__ == '__main__':
    from base64 import b16decode, b16encode

    raw_img = b16decode('424D4E0000000000000036000000280000000300000002000000010018000000000018000000C40E0000C40E00000000000000000000FFFFFF8080800000000000000000FF00FF00FF0000000000', True)

    img = BMP()
    
    img.unpack(raw_img)

    assert img.signature == "BM"
    assert img.file_size == 78
    assert img.offset_pixel_array == 54

    assert img.header_size == 40
    assert img.image_width == 3
    assert img.image_height == 2

    assert img.planes == 1
    assert img.bits_per_pixel == 24
    assert img.image_size == 24

    row1, row2 = img.pixel_rows

    # row2 is the first row from top
    assert row2.pixels == [   0,    0, 0xff, # red (colours in (bgr))
                              0, 0xff,    0, # green
                           0xff,    0,    0, # blue
                          ]

    assert row1.pixels == [0xff, 0xff, 0xff, # white
                           0x80, 0x80, 0x80, # grey
                              0,    0,    0, # black
                        ]

    assert img.pack() == raw_img
