#little by default. CRC in big endian
from packet import Packet
from field import Int, Data, Bits, Ref

types = {
      0: ("management", {
         0 : "assosiation request",
         1 : "assosiation response",
         2 : "reassociation request",
         3 : "reassociation response",
         4 : "probe request",
         5 : "probe response",
         6 : "timming advertisement",
         7 : "reserved",
         8 : "beacon",
         9 : "ATIM",
         10: "disassociation",
         11: "authentication",
         12: "deauthentication",
         13: "action",
         14: "action no ack",
         15: "reserved"
         }),

      1: ("control", {
         7 : "control wrapper",
         8 : "block ack request",
         9 : "block ack",
         10: "PS-poll",
         11: "RTS",
         12: "CTS",
         13: "ACK",
         14: "CF-end",
         15: "CF-end + CF-ack"
         }),
      2: ("data", {
         0 : "data",
         1 : "data + CF-ack",
         2 : "data + CF-poll",
         3 : "data + CF-ack + CF-poll",
         4 : "null",
         5 : "CF-ack",
         6 : "CF-poll",
         7 : "CF-ack + CF-poll",
         8 : "QoS data",
         9 : "QoS data + CF-ack",
         10: "QoS data + CF-poll",
         11: "QoS data + CF-ack + CF-poll",
         12: "QoS null",
         13: "reserved",
         14: "QoS CF-poll",
         15: "QoS CF-ack + CF-poll"
         }),
      3: ("reserved", {})
      }

class FrameControl(Packet):
   version = Bits(2)
   type = Bits(2) 
   subtype = Bits(4)
   to_DS = Bits(1)
   from_DS = Bits(1)
   more_fragments = Bits(1)
   retry = Bits(1)
   power_management = Bits(1)
   more_data = Bits(1)
   protected = Bits(1)
   order = Bits(1)

class TypeLenValue(Packet):
   type = Int(1)
   length = Int(1)
   value = Data(length)

class Management(Packet):
   frame_control = Ref(FrameControl)
   duration = Int(2)
   address_1 = Data(6)  #destination
   address_2 = Data(6)  #source
   address_3 = Data(6)  #~bssid
   sequence_control = Int(2)
   
   body = Data(Packet.END)
   
   #fcs = Int(4)
   
class BeaconBody(Packet):
   # 12 bytes fixeds...
   timestamp = Data(8)
   beacon_interval = Int(2)
   capabilities = Int(2)
   
   # then, list of tagged parameters: [id(1 byte), len(1 byte), data(len bytes)]
   parameters = Ref(TypeLenValue).repeated(
         until=lambda packet, raw, offset: offset >= len(raw),
         when=lambda packet, raw, offset: offset < len(raw))
