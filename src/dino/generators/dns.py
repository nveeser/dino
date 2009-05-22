#!/usr/bin/env python

import sys, os, subprocess
from os.path import join as pjoin

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..")
    
from dino.generators.base import Generator, GeneratorException
from dino.config import load_config
from dino.db import (Device, Port, Rack, Site)


from dino.generators.dnsrecord import *

class DnsError(GeneratorException):
    pass

class DuplicationError(DnsError):
    pass

class DnsGenerator(Generator):
    '''
    Generate TinyDNS files for based on stuff in Database
    '''
    NAME = "dns"

    def get_svn_uri(self, svn_uri, filepath):
        self.check_call(['svn', 'export', svn_uri, filepath])

                    
    def query_dynamic_set(self):
        dynamic = list()
        
        sess = self.db_config.session()
        
        self.log.info("Looking for blessed interfaces")
        ports = sess.query(Port).filter_by(is_blessed=True)\
            .join(Device).join(Rack).join(Site).filter_by(name=self.settings.site).all()            
        self.log.info("Found %d blessed ports" % len(ports))
            
        for port in ports:
            
            if port.interface is None:
                self.log.warn("Skipping Port with no Interface: " % port)
                continue
            
            host = port.device.host
            device = port.device
            
            rec = FullARecord()
            rec.fqdn = "%s.%s.%s.%s" % (host.name, host.pod.name, host.site.name, self.settings.domain) 
            rec.ip = port.interface.address.value
            dynamic.append(rec)
            
            rec = ForwardARecord()
            rec.fqdn = "slot%s.rack%s.%s.%s" % (device.rackpos, device.rack.name, device.site.name, self.settings.domain)
            rec.ip = port.interface.address.value
            dynamic.append(rec)
            
            
        self.log.info("Looking for IPMI interfaces")
        ports = sess.query(Port).filter_by(is_ipmi=True)\
            .join(Device).join(Rack).join(Site).filter_by(name=self.settings.site).all()
            
        self.log.info("Found %d ipmi ports" % len(ports))
        
        for port in ports:
            
            if port.interface is None:
                self.log.warn("Skipping Port with no Interface: " % port)
                continue
                
            host = port.device.host            
            rec = FullARecord()
            rec.fqdn = "ipmi-%s.%s.%s.%s" % (host.name, host.pod.name, host.site.name, self.settings.domain) 
            rec.ip = port.interface.address.value
            dynamic.append(rec)
            
            device = port.device
            rec = ForwardARecord()
            rec.fqdn = "ipmi-slot%s.rack%s.%s.%s" % (device.rackpos, device.rack.name, device.site.name, self.settings.domain)
            rec.ip = port.interface.address.value
            dynamic.append(rec)
            
        sess.close()
        return dynamic
    
    
    def check_sets(self, static_set, dynamic_set):
        #
        # Check Records
        # 
        overlap = static_set & dynamic_set
        
        if len(overlap) > 0:
            self.log.warning("The following records are duplicated in static and dynamic files")
            for r in overlap:
                dynamic_set.remove(r) 
                self.log.warning(r)                
            
        #
        # Anything else we should do here?
         
            
    def generate(self):
        #
        # Setup base work dir
        # 
        self.setup_dir(self.workdir)
        
        #
        # Pull Static files from SVN
        #
        internal_fp = pjoin(self.workdir, 'static-internal')
        shared_fp = pjoin(self.workdir, 'static-shared')
        
             
        self.get_svn_uri(self.settings.dns_internal_uri, internal_fp)   
        self.get_svn_uri(self.settings.dns_shared_uri, shared_fp)
        
        internal_recs = DnsRecord.parse_data_file(internal_fp)
        shared_recs = DnsRecord.parse_data_file(shared_fp)
        static_set = set( internal_recs + shared_recs )
        
        dynamic = self.query_dynamic_set()
    
        #
        # check static and dynamic files
        #  
        self.check_sets(static_set, set(dynamic))


        #
        # Write the output file
        #        
        self.setup_dir(self.workdir)
        output_fp = pjoin(self.workdir, self.settings.dns_combinded_file)
        
        self.log.info("Writing output file: %s" % output_fp) 
        f = open(output_fp, 'w')
        
        x = open(internal_fp)
        f.write(x.read())
        x.close()
        
        x = open(shared_fp)
        f.write(x.read())
        x.close()
        
        f.write("\n")
        f.write("#\n")
        f.write("# Begin dynamically generated records\n")
        f.write("#\n")
        f.write("\n")
        
        dynamic.sort()        
        for r in dynamic:
            f.write(str(r) + "\n")

        f.close()


    def activate(self):
        script_path = pjoin(os.path.abspath(os.path.dirname(__file__)), 'activate_dns.sh')
        p = subprocess.Popen([script_path], stdout=subprocess.PIPE, 
            env={'MW_BLESSED_PORT' : self.settings.dns_blessed_port})
        p.wait()
        if p.returncode != 0:
            (out, err) = p.communicate()
            print "STDOUT: "
            print out
            print "STDERR: "
            print err            
            raise Exception("%s returned non 0 ret: %s" % (script_path, p.returncode))
        return p.returncode


    
if __name__ == '__main__':
    DnsGenerator.main()
