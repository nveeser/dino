import os,sys
import pcapy

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")

from dino.probe.impl import Probe
from packet import Ethernet
from packet.cdp import CDP, Vlan, PortId, DeviceId, Platform, Addresses, Duplex


DEFAULT_MAP = { 
    'switch' : None,
    'vlan' : None,
    'port' : None,  
    'address' : None,
    'duplex' : None,
    'platform' : None,         
}   
    

class CDPProbe(Probe):    
    NAME = "cdp"
    
    CACHE_PATH = "/tmp/dino_cdp_probe.pcap"
    DEVICE_DEFAULT = "eth0"
    
    def __init__(self, **kwdict):
        super(CDPProbe, self).__init__(kwdict)
        self.cache_filename = kwdict.get('cache_file', self.CACHE_PATH)
        self.device_name = kwdict.get('device', self.DEVICE_DEFAULT)
        
        self.result = DEFAULT_MAP.copy()
        
    def run(self):
        if os.path.exists(self.cache_filename):        
            self._read_cache_file()
        else:
            self._probe_network()

        if self.frame.contains_header(CDP):    
            c = self.frame.find_header(CDP)

            self.result['switch'] = c.find_tlv_data(DeviceId)
            
            self.result['platform'] = c.find_tlv_data(Platform)
            
            self.result['port'] = c.find_tlv_data(PortId)
            
            self.result['vlan'] = c.find_tlv_data(Vlan)
            
            self.result['duplex'] = c.find_tlv_data(Duplex)
            
            tlv = c.find_tlv(Addresses)
            if tlv is not None and len(tlv.addrs) > 0:
                self.result['address'] = str(tlv.addrs[0])
                            
                        
        return self.result
                
    def _probe_network(self):        
        ifs = pcapy.findalldevs()        
        if 0 == len(ifs):   
            print "You don't have enough permissions to open any interface on this system."
            sys.exit(1)

        reader = pcapy.open_live(self.device_name, 10000, 1, 60)
        self.dumper = reader.dump_open(self.cache_filename)
        # set the special CDP filter in PCAP
        reader.setfilter("ether[20:2] == 0x2000")
        
        try: 
            reader.dispatch(1, self._handle_dispatch)
        except KeyboardInterrupt, e:
            os.unlink(self.cache_filename)
            self.dumper.close()
            return None
                
    def _read_cache_file(self):
        self.log.info("Using existing file: %s" % self.cache_filename)
        reader = pcapy.open_offline(self.cache_filename)
        (hdr, data) = reader.next()        
        self.frame = Ethernet.create(data)

    def _handle_dispatch(self, hdr, data):
        if self.dumper:
            self.dumper.dump(hdr, data)            
        self.frame = Ethernet.create(data)
  
  
if __name__=='__main__':    
    probe = CDPProbe(device="eth0")

    print probe.run()

    
