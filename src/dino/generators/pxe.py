#!/usr/bin/env python
"""
"""

import sys
import os
import socket
from os.path import join as pjoin

from dino.generators.base import Generator
from dino.db import (Host, Rack, Device, Site)

HOST_TEMPLATE = \
"""ipappend 1
default %(kernel)s
timeout 30

label %(kernel)s
kernel kernels/%(kernel)s
append initrd=%(initrd)s \
state=%(rapids_state_src)s \
nfsroot=%(seed_server)s:/nfsroot/gentoo/%(rapids_ver)s \
source=https://svn.metaweb.com:/svn/rapids/ \
squash=%(squash_ver)s \
seed=%(seed_server)s \
ip=dhcp \
console=tty0 \
%(extra_console)s \
tag=%(os_codename)s \
hn=%(fqdn)s \
%(options)s
"""

NONIPMI_CONSOLE = 'console=ttyS0,38400n8'
IPMI_CONSOLE = 'console=ttyS1,57600n8'
VGA_CONSOLE = ''
class PxeGenerator(Generator):
    NAME = "pxe"
    
    
    data = {
        'console_settings' : None,
        'kernel' : None,
        'mac' : None, 
        'rapids_ver' : 3,        
        'options' : "",
        'seed_server' : None,
        'fqdn' : None,
        'initrd' : None,
        'squash_ver' : None,
        'rapids_state_src' : None,       
    }
    
    def query(self):
        
        self.data['seed_server'] = socket.gethostbyname(socket.gethostname())
        
        session = self.db_config.session() 
     
        dc_info = self.pull_rapids_datacenter(self.settings, self.settings.site)
        
        for host in session.query(Host)\
            .join(Device).filter_by(hw_class='server')\
            .join(Rack).join(Site).filter_by(name=self.settings.site).all():
            
            self.log.info("Process Host: %s", host)
            data = dict(self.data)
            data['kernel'] = data['os_codename'] = host.appliance.os.name
            data['fqdn'] = host.hostname() + "." + self.settings.domain            

            data['initrd'] = self.settings.pxe_initrd
            data['squash_ver'] = self.settings.pxe_squash_ver
            data['rapids_ver'] = self.settings.pxe_rapids_ver
            data['options'] = 'ns_resolution=metaweb.com:%s' % ':'.join(dc_info['ns'])
            data['rapids_state_src'] = self.settings.pxe_rapids_state_source
            for p in host.device.ports:
                if p.is_blessed:
                    data['mac'] = p.mac                
                
                if p.is_ipmi:
                    data['extra_console'] = IPMI_CONSOLE
                else:
                    data['extra_console'] = NONIPMI_CONSOLE
                
            if host.device.hw_type == "vm":
                data['extra_console'] = VGA_CONSOLE    
                              
            yield data
            
        session.close()

    def generate(self):
    
        self.log.info("generate: started")        
        
        self.setup_dir(self.workdir)
           
        for data in self.query():
            self.log.info("  Host: %s" % data['fqdn'])
          
            # goofy pattern admittedly, but this is what pxe requires; 01-mac
            filename = '01-%s' % data['mac'].lower().replace(':', '-')
            fp = pjoin(self.workdir, filename)
            
            self.log.fine("      Filename: %s", fp)        
            f = open(fp, 'w')
            f.write(HOST_TEMPLATE % data)
            f.close()

            sympath = pjoin(self.workdir, "host-%s" % data['fqdn'])
            self.log.fine("      Symlink : %s", sympath)
            os.symlink(filename, sympath)
    
        self.log.info("generate: completed")
    
    def activate(self):
        pxe_dir = self.settings.pxe_conf_dir

        self.log.info("activate: starting run updating %r from %r", pxe_dir, self.workdir)
        self.rsync_directory(self.workdir, pxe_dir, extra_args=('--exclude=default',))
        self.log.info("activate: finished updating %r", pxe_dir)
    
    
    
if __name__ == '__main__':
    PxeGenerator.main()