
import struct
from packet.header import Header
from packet.ethernet import EthernetSNAP

                
class CDP(Header):
    CONTAINERS = { EthernetSNAP : (0x00000c, 0x2000) }
    
    def __init__(self, parent, buffer, idx):
        super(CDP,self).__init__(parent, buffer, idx)

        self.cdp_version = buffer.byte(idx)
        self.cdp_ttl = buffer.byte(idx+1)
        self.cdp_checksum = buffer.word(idx+2)

        self._parse_tlv(buffer, idx+4)
        
    def _parse_tlv(self, buffer, idx):
        self._items = []

        packet_size = buffer.size()
        while idx < packet_size:
            (type, length) = (buffer.word(idx), buffer.word(idx+2))
            if idx+length > packet_size:
                raise Exception("TLV Parsing Error: TypeValue extends beyond packet length") 
            data = self.buffer.bytes()[idx+4:idx+length]            
            idx += length

            item = TypeValue.create_typevalue(type, data)
            self._items.append(item)

    def iterate_tlvs(self):
        for item in self._items:
            yield item

    def find_tlv(self, cls):
        for item in self._items:
            if item.__class__ == cls:
                return item
        
        return None

    def find_tlv_data(self, cls):
        tlv = self.find_tlv(cls)
        if tlv is not None:
            return tlv.data
        else:
            return None


class TypeValueMeta(type):    
    def __init__(cls, name, bases, dict_):        
        super(TypeValueMeta, cls).__init__(name, bases, dict_) 

        if bases[0] == object:
            cls.TYPE_MAP = {}    
            
        if not dict_.has_key("NAME"):
            setattr(cls, "NAME", name)

        if cls.TYPE_ID == None:
            return 

        cls.TYPE_MAP[cls.TYPE_ID] = cls


class TypeValue(object):
    __metaclass__ = TypeValueMeta
    TYPE_ID = None

    @classmethod
    def create_typevalue(cls, type, data):
        if cls.TYPE_MAP.has_key(type):
            return cls.TYPE_MAP[type](data)
        else:
            return cls.TYPE_MAP[0](type, data)
    
    def __init__(self, data):
        self.data = self.parse(data)
        
    
    def parse(self, data):
        return data

    def __str__(self):
        return "%s(0x%04x): %s" % (self.NAME, self.TYPE_ID, self.data)


class StringTypeValue(TypeValue):
    TYPE_ID = None

    def parse(self, data):
        return "".join(map(chr, data))


class IntTypeValue(TypeValue):
    TYPE_ID = None
    def parse(self, data):
        for fmt in [ "!B", "!H", "!I", "!L" ]:
            if struct.calcsize(fmt) == len(data):
                (value, ) = struct.unpack(fmt, data.tostring())
                return value
            
        return data

class BitFieldTypeValue(IntTypeValue):
    TYPE_ID = None

    def parse(self, data):
        num = super(BitFieldTypeValue, self).parse(data)
        return "0x%04x" % num

##################################################################
# Real Types
#

class Unknown(TypeValue):                                    
    TYPE_ID = 0x0000
    
    def __init__(self, type_id, data):
        super(Unknown, self).__init__(data)
        self.type_id = type_id

    def __str__(self):
        return "%s(0x%04x): %s" % (self.NAME, self.type_id, Header.hex2str(self.data))

class DeviceId(StringTypeValue):
    TYPE_ID = 0x0001

    
class AddressSet(TypeValue):
    TYPE_ID = None
    
    def parse(self, data):
        self.addrs = []

        (count,) = struct.unpack("!I", data[0:4].tostring())
        idx = 4
        
        for i in xrange(0,count):
            
            (type, length) = struct.unpack("!BB", data[idx:idx+2].tostring())
            idx += 2
            
            protocol = Header.hex2int( data[idx:idx+length] )
            idx += length
            
            (length,) = struct.unpack("!H", data[idx:idx+2].tostring())
            idx += 2
            
            addr = data[idx:idx+length]
            idx += length        
            
            for cls in [ self.IPv4Addr, self.IPv6Addr ]:
                if cls.PROTO == protocol:
                    value = cls(addr, protocol)
                    self.addrs.append(value)

        return "(%s)" % ", ".join(map(str, self.addrs)) 
        
    class IPv4Addr(object):
        PROTO = 0xCC        
        def __init__(self, addr, proto):
            self._value = addr
            self._proto = proto
        def __str__(self):
            return ".".join(map(lambda x: "%d" % int(x), self._value))
            
    class IPv6Addr(object):
        PROTO = 0x0800

class Addresses(AddressSet):
    TYPE_ID = 0x0002
        
class PortId(StringTypeValue):
    NAME = "Port ID"
    TYPE_ID = 0x0003

class Capabilities(TypeValue):    
    TYPE_ID = 0x0004

    CAP_SET = { 0x01 : "ROUTER",
                0x02 : "TRANSPARENT_BRIDGE",
                0x04 : "SOURCE_BRIDGE",
                0x08 : "SWITCH",
                0x10 : "HOST",
                0x20 : "IGMP",
                0x40 : "REPEATER" }

    def parse(self, data):
        (num,) = struct.unpack('!I', data.tostring())
        return [ self.CAP_SET[bit] for bit in self.CAP_SET.keys() if num & bit > 0 ]                                 

        
class Version(StringTypeValue):
    TYPE_ID = 0x0005

class Platform(StringTypeValue):
    TYPE_ID = 0x0006

class IPPrefix(TypeValue):
    NAME = "IP Prefix"
    TYPE_ID = 0x0007

class VTPManagementDomain(StringTypeValue):
    TYPE_ID = 0x0009

class Vlan(IntTypeValue):
    TYPE_ID = 0x000a

class Duplex(TypeValue):
    TYPE_ID = 0x000b
    DUPLEX_MAP = { 0x00 : "Half",
                   0x01 : "Full"}
    
    def parse(self, data):
        return self.DUPLEX_MAP[data[0]]
    

class ApplianceReply(TypeValue):
    TYPE_ID = 0x000e

class ApplianceQuery(TypeValue):
    TYPE_ID = 0x000f

class MTU(IntTypeValue):
    TYPE_ID = 0x0011

class ExtendedTrust(BitFieldTypeValue):
    TYPE_ID = 0x0012

class UntrustedCOS(BitFieldTypeValue):
    TYPE_ID = 0x0013

class SystemName(TypeValue):
    TYPE_ID = 0x0014

class SystemOID(TypeValue):
    TYPE_ID = 0x0015

class ManagementAddress(AddressSet):
    TYPE_ID = 0x0016

class Location(TypeValue):
    TYPE_ID = 0x0017

class Power(TypeValue):
    TYPE_ID = 0x001a
    def __init__(self, data):
        super(Power, self).__init__(data)
        (self.request_id, self.mgmt_id, self.available, self.available2) = struct.unpack("!HHII", data.tostring())
        
    def __str__(self):
        return "%s(0x%04x): Request: %d MgmtId: %d Power: %d mw Power: %d mw" % (self.NAME, self.TYPE_ID, self.request_id, self.mgmt_id, self.available, self.available2)



