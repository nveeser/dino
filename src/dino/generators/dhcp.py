#!/usr/bin/env python
"""
"""

import os
import subprocess
import sys
import socket 
from os.path import join as pjoin

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..")

from dino.generators.base import Generator, GeneratorQueryError
from dino.db import (Rack, Device, Port, Site, Subnet, IpType)
 
GLOBAL_TEMPLATE = \
"""allow booting;
allow bootp;
ddns-update-style none;
option dhcp-max-message-size 2048;
use-host-decl-names on;

option space pxelinux;
option pxelinux.magic      code 208 = string;
option pxelinux.configfile code 209 = text;
option pxelinux.pathprefix code 210 = text;
option pxelinux.reboottime code 211 = unsigned integer 32;
vendor-option-space pxelinux;  


option domain-name "%(domain-name)s";
option domain-name-servers %(domain-name-servers)s;
option time-servers %(time-servers)s;
option ntp-servers %(ntp-servers)s;

# Defaults for unknown hosts
#
filename "%(def_filename)s";
next-server %(def_next-server)s;
server-name "%(def_server-name)s";

"""


    
SUBNET_TEMPLATE = \
"""subnet %(subnet)s netmask %(subnet-mask)s {
    option routers %(routers)s;
    option subnet-mask %(subnet-mask)s;
    option broadcast-address %(broadcast-address)s;
    %(options)s
}
"""

HOST_FEDORA_TEMPLATE = \
'''host %(hostname)s {
    hardware ethernet %(mac)s;
    fixed-address %(ip)s;
    option pxelinux.pathprefix "%(path_prefix)s/";
    option pxelinux.configfile "%(config_file)s";
}
'''

HOST_TEMPLATE = \
"""host %(hostname)s {
    hardware ethernet %(mac)s;
    fixed-address %(ip)s;
    option root-path "/nfsroot/gentoo/%(rapids_ver)s,rsize=8192,wsize=8192,acregmin=1800,acregmax=1800,acdirmin=1800,acdirmax=1800";
    filename "%(boot_filename)s";
    %(options)s
}
"""


IPMI_TEMPLATE = \
"""host %(hostname)s {
    hardware ethernet %(mac)s;
    fixed-address %(ip)s;
    %(options)s
}
"""
    

class DhcpGenerator(Generator):
    NAME = "dhcp"

    def query_global(self):
        data = {   
            'domain-name-servers' : None, 
            'time-servers' : None,
            'ntp-servers' : None,
            'domain-name' : None,             

            'filename' : None,
            'next-server' : None,
            'server-name' : None,          
        }
        seed_ip = socket.gethostbyname(socket.gethostname())
        
        dc_info = self.pull_rapids_datacenter(self.settings, self.settings.site)
        data['domain-name-servers'] = ", ".join(dc_info['ns'])
        data['time-servers'] = ", ".join(dc_info['ntp'])
        data['ntp-servers'] = ", ".join(dc_info['ntp'])
        data['domain-name'] = self.settings.domain
        data['def_filename'] = self.settings.dhcp_boot_filename
        data['def_next-server'] = seed_ip
        data['def_server-name'] = socket.getfqdn()
        
        return data
        

    def query_subnets(self, session):
        
        base_data = {
            'subnet' : None,
            'subnet-mask' : None,
            'routers' : None, 
            'broadcast-address' : None,
            'options' : None,             
        }
                
        data = dict(base_data)
        
        dc_info = self.pull_rapids_datacenter(self.settings, self.settings.site)
        
        subnets = session.query(Subnet).join(Site).filter_by(name=self.settings.site).all()        
        for s in subnets:
            self.log.fine("  Subnet: %s" % s.addr)
            data['subnet'] = s.addr
            data['subnet-mask'] = s.mask
            
            data['routers'] = IpType.ntoa(s.naddr + s.gateway)
            data['broadcast-address'] = IpType.ntoa(s.broadcast)


            data['options'] = ""
            
            for r in s.ranges:
                self.log.fine("   Range: %s", r)
                if r.range_type == 'dhcp':
                    data['options'] += "range %s %s;\n" % (r.start_addr, r.end_addr)
                            
            yield self.check_data(data)


            
    def query_hosts(self, session):
                      
        base_data = {
            'hostname' : None,
            'mac' : None, 
            'ip' : None, 
            'rapids_ver' : None,
            'boot_filename' : None, 
            'options' : None,
        }
        
        data = dict(base_data)
        
        ports = session.query(Port).filter_by(is_blessed=True)\
            .join(Device).join(Rack).join(Site)\
            .filter_by(name=self.settings.site)\
            .filter(Device.host!=None).all()
        for port in ports:    
            if port.interface is None:
                self.log.info("Skipping Port with no Interface: " % port)
                continue
                    
            data['hostname'] = port.device.host.hostname() + "." + self.settings.domain            
            data['ip'] = port.interface.address.value
            data['mac'] = port.mac
            data['boot_filename'] = self.settings.dhcp_boot_filename
            data['rapids_ver'] = str(self.settings.dhcp_rapids_ver)
            data['options'] = ""
            self.log.fine("   Host: %s", data['hostname'])
            
            yield self.check_data(data)
            
    

    def query_ipmi_hosts(self, session):    
        
        base_data = {
            'hostname' : None,
            'mac' : None,
            'ip' : None, 
            'additional-options' : "",
        }
    
        data = dict(base_data)    
            
        ports = session.query(Port).filter_by(is_ipmi=True)\
            .join(Device).join(Rack).join(Site)\
            .filter(Site.name==self.settings.site)\
            .filter(Device.host!=None).all()
            
        for port in ports:
            if port.interface is None:
                self.log.info("Skipping Port with no Interface: " % port)
                continue
            data['hostname'] = "ipmi-%s.%s" % (port.device.host.hostname(), self.settings.domain)
            data['mac'] = port.mac
            data['ip'] = port.interface.address.value
            data['options'] = ""
            self.log.fine("   IpmiHost: %s", data['hostname'])
            
            yield self.check_data(data)
        
    
    def check_data(self, data):
        for name, value in data.iteritems():
            if value is None:
                raise GeneratorQueryError("Missing Data in map %s: %s" % (data, name))
        return data


    def generate(self):
                 
        write_loc = pjoin(self.workdir, 'dhcpd.conf')
        self.setup_dir(self.workdir)
        
        session = self.db_config.session()
        # currently not possible to fail; except wrap it when it becomes
        # possible.
        generated_config = []


        global_section = GLOBAL_TEMPLATE % self.query_global()
        generated_config.append(global_section)

        self.log.info("generate: reading subnets")        
        sections = [ SUBNET_TEMPLATE % d for d in self.query_subnets(session) ] 
        generated_config.extend(sections)
        
        self.log.info("generate: reading hosts")
        sections = [ HOST_TEMPLATE % d for d in self.query_hosts(session) ] 
        generated_config.extend(sections)
        
        self.log.info("generate: reading ipmi hosts")
        sections = [ IPMI_TEMPLATE % d for d in self.query_ipmi_hosts(session) ] 
        generated_config.extend(sections)
                                

        self.log.info("generate: updating %r", write_loc)
        
        f = open(write_loc, 'w')
        f.write('\n'.join(generated_config))
        f.close()
        
        self.log.info("generate: completed")
    
    
    
    
    def activate(self):
        write_loc = self.settings.dhcp_conf_loc
        init_loc = self.settings.dhcp_init_loc
    
        self.log.info("activate: starting transfer")
    
        f = open(pjoin(self.workdir, 'dhcpd.conf'), 'r')
        data = f.read()
        f.close()
        
        f = open(write_loc, 'w')
        f.write(data)
        f.close()

        self.log.debug("activate: config updated")
 
        self.check_call([init_loc, 'restart'])

        self.log.debug('activate: service %r restarted', init_loc)
        self.log.info('activate: completed')





if __name__ == '__main__':
    DhcpGenerator.main()
    
    