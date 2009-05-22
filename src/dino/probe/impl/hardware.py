
import os,sys
from subprocess import Popen, PIPE

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    
from dino.probe.impl import Probe

from lxml import etree
import xml.dom.minidom
    
class HardwareProbe(Probe):   
    LSHW_PATH="/usr/sbin/lshw"
    CACHE_PATH="/tmp/dino_hardware.xml"
     
    DEFAULT_RESULT = {
        'vendor' : None,    
        'product' :   None,        
        'serial' : None,
        'processors' : [],
        'memory' : [],
        'ports' : [],
        
    }
     
    def __init__(self, **kwargs):
        self._cache_filename = kwargs.get("cache-file", self.CACHE_PATH)
        
        self.result = self.DEFAULT_RESULT 
     
    def _read_hardware_info(self): 
        if not os.path.exists(self._cache_filename):
            p = Popen([self.LSHW_PATH, "-xml"], stdout=PIPE)
            (output,err) = p.communicate()
            p.close()
            f = open(self._cache_filename, "w")
            f.write(output)
            f.close()
        else:
            f = open(self._cache_filename)
            output = f.read()
            f.close()
            
        return output
            
    def _find_system(self, root):        
        system = root.find("node")
        self.result['product'] = system.findtext("product")
        self.result['vendor']= system.findtext("vendor")
        self.result['serial']= system.findtext("serial")
        
    def _find_processor(self, root):
        
        for proc in root.xpath("//node[@class='processor']"):
            proc_map = {}
            proc_map['name'] = proc.findtext("product")
            proc_map['speed'] = proc.findtext("size")
            
            self.result['processors'].append(proc_map)
        
    def _find_memory(self, root):
        (memory,) = root.xpath("/node[@class='system']/node[@class='bus']/node[@id='memory']")
        #size = int(size) / 1024 / 1024 / 1024
        self.result['memory'] = memory.findtext('size')
    
    def _find_network_ports(self, root):
        for port in root.xpath("//node[@class='network']"):
            port_map = {}
            port_map['phy_id'] = port.findtext("physid")
            port_map['if_name'] = port.findtext("logicalname")
            port_map['mac'] = port.findtext("serial")
            port_map['ip'] = port.xpath("./configuration/setting[@id='ip']/@value")
            port_map['link'] = port.xpath("./configuration/setting[@id='link']/@value")
            print port_map['link']
            
            self.result['ports'].append(port_map)
            
    def run(self):
        xml_info = self._read_hardware_info()        
        root = etree.fromstring(xml_info)
        #xpatheval = etree.XPathEvaluator(root)

        self._find_system(root)
                
        self._find_processor(root)
        
        self._find_memory(root)
                        
        self._find_network_ports(root)
        
        #for node in root.xpath("//node"):            
            #print node.attrib['id'], node.findtext("description"), node.findtext("product") 

                                
        return self.result
    

if __name__=='__main__':    
    p = HardwareProbe()  
    print p.run()