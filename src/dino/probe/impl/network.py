import os,sys
from subprocess import Popen, PIPE
import re

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")

from dino.probe.impl import Probe


class NetworkProbe(Probe):
    SYS_ROOT="/sys/class/net"
    
    def __init__(self, **kwargs):
        super(NetworkProbe, self).__init__(**kwargs)
        
        
        self.result = { 
            'blessed_port' : None,
            'ports' : None, 
        }
    
    def _read_file(self, filename):
        assert os.path.exists(filename)
        
        f = open(filename)
        try:
            return f.read()
        finally:
            f.close()
        
    """
        /sysfs/class/net/<ifname>/*
            net/core/sysfs.c
            linux/include/netdevice.h        
        
        flags: linux/include/if.h
        operstate:   rfc2863
        features: linux/include/netdevice.h
        type: include/linux/if_arp.h
        
    """
    
    re.compile(".*:\s(?P<ifindex>\d+)\s" )

    def run(self):
        ifs_list = os.listdir(self.SYS_ROOT)
        
        for ifs in ifs_list:
            p = Popen(["/sbin/ip", "link", "show", ifs], stdout=PIPE)
            (output,err) = p.communicate()
            print "%s: %s" % (ifs, output)
    
    
    
if __name__ == "__main__":
    p = NetworkProbe()
    r = p.run()
    
    print r