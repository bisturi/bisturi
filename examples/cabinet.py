from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
sys.path.append("../")

from bisturi.packet import Packet
from bisturi.field  import Bits, Int, Data, Ref

# TODO(s):
#  - flags and byte order, works?
#  - one packet reference the fields of another (like Folder referencing to Header), it is possible to implement?

class HeaderFlags(object):
   PREV_CABINET    = 0x0001
   NEXT_CABINET    = 0x0002
   RESERVE_PRESENT = 0x0004

class Header(Packet):
    __bisturi__ = {'endianness': 'little'}

    signature = Data(4, default=b'MSCF')

    reserved1 = Int(4)
    size_of_cabinet = Int(4)
    reserved2 = Int(4)
    offset_first_file = Int(4)
    reserved3 = Int(4)

    version_minor = Int(1)
    version_major = Int(1)

    number_of_folders = Int(2)
    number_of_files = Int(2)

    flags = Int(2)

    set_id = Int(2) # must be the same for all cabinets in a set
    cabinet_id = Int(2) # number of this cabinet file in a set 
    
    size_reserved_area_per_cabinet   = Int(2).when(flags & HeaderFlags.RESERVE_PRESENT)  
    size_reserved_area_per_folder    = Int(1).when(flags & HeaderFlags.RESERVE_PRESENT)
    size_reserved_area_per_datablock = Int(1).when(flags & HeaderFlags.RESERVE_PRESENT)

    # (optional) per-cabinet reserved area
    reserved_area = Data(size_reserved_area_per_cabinet).when(flags & HeaderFlags.RESERVE_PRESENT) 

    name_previous_cabinet = Data(until_marker=b'\0').when(flags & HeaderFlags.PREV_CABINET)
    name_previous_disk = Data(until_marker=b'\0').when(flags & HeaderFlags.PREV_CABINET)
    name_next_cabinet = Data(until_marker=b'\0').when(flags & HeaderFlags.NEXT_CABINET)
    name_next_disk = Data(until_marker=b'\0').when(flags & HeaderFlags.NEXT_CABINET)


class DataBlock(Packet):
   __bisturi__ = {'endianness': 'little'}

   checksum = Int(4)
   size_compressed = Int(2)
   size_uncompressed = Int(2)

   reserved_area = Data(lambda root, **k: root.size_reserved_area_per_datablock)\
                       .when(lambda root, **k: root.flags & HeaderFlags.RESERVE_PRESENT)

   data = Data(size_compressed)


class Folder(Packet):
   __bisturi__ = {'endianness': 'little'}

   offset_first_datablock = Int(4)
   number_of_datablocks = Int(2)
   compression_type = Int(2)
   
   reserved_area = Data(lambda root, **k: root.pkt.size_reserved_area_per_folder)\
                       .when(lambda root, **k: root.flags & HeaderFlags.RESERVE_PRESENT)

   datablocks = Ref(DataBlock).repeated(number_of_datablocks)\
                  .at(offset_first_datablock)


class File(Packet):
   __bisturi__ = {'endianness': 'little'}

   uncompressed_size = Int(4)
   uncompressed_offset_of_this_in_folder = Int(4)
   index_of_folder = Int(2)
   date = Int(2)
   time = Int(2)
   attributes = Int(2)
   name = Data(until_marker=b'\0')



class Cabinet(Packet):
   __bisturi__ = {'endianness': 'little'}

   header  = Ref(Header, embeb=True)
   folders = Ref(Folder).repeated(lambda root, **k: root.number_of_folders)

   files = Ref(File).repeated(lambda root, **k: root.number_of_files)\
            .at(lambda root, **k: root.offset_first_file)


if __name__ == '__main__':
   from base64 import b16decode

   # example from https://msdn.microsoft.com/en-us/library/bb417343.aspx
   raw_file = b16decode(b'4d53434600000000fd000000000000002c000000000000000301010002000000220600005e000000010000004d0000000000000000006c22ba59200068656c6c6f2e63004a0000004d00000000006c22e759200077656c636f6d652e6300bd5aa6309700970023696e636c756465203c737464696f2e683e0d0a0d0a766f6964206d61696e28766f6964290d0a7b0d0a202020207072696e7466282248656c6c6f2c20776f726c64215c6e22293b0d0a7d0d0a23696e636c756465203c737464696f2e683e0d0a0d0a766f6964206d61696e28766f6964290d0a7b0d0a202020207072696e7466282257656c636f6d65215c6e22293b0d0a7d0d0a0d0a', True)
   
   cabinet_file = Cabinet.unpack(raw_file)

   assert cabinet_file.signature == b'MSCF'

   assert cabinet_file.size_of_cabinet == 253
   assert cabinet_file.offset_first_file == 0x0000002c

   assert cabinet_file.version_minor == 3
   assert cabinet_file.version_major == 1

   assert cabinet_file.number_of_folders == 1
   assert cabinet_file.number_of_files ==   2

   assert cabinet_file.flags == 0

   assert cabinet_file.set_id == 0x0622
   assert cabinet_file.cabinet_id == 0
   
   assert cabinet_file.size_reserved_area_per_cabinet   == None
   assert cabinet_file.size_reserved_area_per_folder    == None
   assert cabinet_file.size_reserved_area_per_datablock == None

   assert cabinet_file.reserved_area == None

   assert cabinet_file.name_previous_cabinet == None
   assert cabinet_file.name_previous_disk == None
   assert cabinet_file.name_next_cabinet == None
   assert cabinet_file.name_next_disk == None

   assert len(cabinet_file.folders) == 1
   assert len(cabinet_file.files) == 2

   folder = cabinet_file.folders[0]
   assert folder.offset_first_datablock == 0x0000005e
   assert folder.number_of_datablocks == 1
   assert folder.compression_type == 0 # none compression
   
   assert folder.reserved_area == None
   assert len(folder.datablocks) == 1

   datablock = folder.datablocks[0]
   assert datablock.checksum == 0x30a65abd
   assert datablock.size_compressed == 151
   assert datablock.size_uncompressed == 151

   assert datablock.reserved_area == None
   assert datablock.data == b'''#include <stdio.h>\r\n\r\nvoid main(void)\r\n{\r\n    printf("Hello, world!\\n");\r\n}\r\n#include <stdio.h>\r\n\r\nvoid main(void)\r\n{\r\n    printf("Welcome!\\n");\r\n}\r\n\r\n'''

   file1 = cabinet_file.files[0]
   assert file1.uncompressed_size == 77
   assert file1.uncompressed_offset_of_this_in_folder == 0x00000000
   assert file1.index_of_folder == 0
   assert file1.date == 0x226c   # March 12, 1997
   assert file1.time == 0x59ba   # 11:13:52 AM
   assert file1.attributes == 0x0020
   assert file1.name == b"hello.c"

   file2 = cabinet_file.files[1]
   assert file2.uncompressed_size == 74
   assert file2.uncompressed_offset_of_this_in_folder == 0x0000004d
   assert file2.index_of_folder == 0
   assert file2.date == 0x226c   # March 12, 1997
   assert file2.time == 0x59E7   # 11:15:14 AM
   assert file2.attributes == 0x0020
   assert file2.name == b"welcome.c"

   assert cabinet_file.pack() == raw_file

