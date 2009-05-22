
from packet.header import Header, PacketBuffer

class Ethernet(Header):
                
    def __init__(self, parent, buffer, idx):
        super(Ethernet, self).__init__(parent, buffer, idx)
        self.eth_dest = buffer.bytes()[idx:idx+6]
        self.eth_src = buffer.bytes()[idx+6:idx+12]        
        
    @staticmethod
    def create(data,idx=0):
        buffer = PacketBuffer(data)
        value = buffer.word(idx+12)
        if value >= 0x800:
            return EthernetII(None, buffer, idx)
        else:
            return EthernetLLC(None, buffer, idx)
        
    @staticmethod
    def eth2str(bytes):                
        l = map(lambda x: "%02x" % x, bytes)
        return ":".join(l)


class EthernetII(Ethernet):
    def __init__(self, parent, buffer, idx=0):
        super(EthernetII ,self).__init__(parent, buffer, idx)        

        self.ethertype = buffer.word(idx+12)
        
        key = self.ethertype
        self.parse_child(key, 13)


class EthernetLLC(Ethernet):    

    def __init__(self, parent, buffer, idx=0):
        super(EthernetLLC ,self).__init__(parent, buffer, idx)

        self.length = buffer.word(idx+12)
        self.llc_dsap = buffer.byte(idx+14)
        self.llc_ssap = buffer.byte(idx+15)
        self.llc_cf = buffer.byte(idx+16)
        
        key = (self.llc_dsap, self.llc_ssap, self.llc_cf) 
        self.parse_child(key, 17)


class EthernetSNAP(Header):    
    CONTAINERS = { EthernetLLC : (0xaa,0xaa,0x03) }

    def __init__(self, parent, buffer, idx):
        super(EthernetSNAP ,self).__init__(parent, buffer, idx)
        
        self.snap_orgid = Header.hex2int(buffer.bytes()[17:20])
        self.snap_pid = Header.hex2int(buffer.bytes()[20:22])
        
        key = (self.snap_orgid, self.snap_pid)
        self.parse_child(key, 22)
