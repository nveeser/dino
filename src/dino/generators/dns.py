#!/usr/bin/env python

import sys
import os
import subprocess
import re
from os.path import join as pjoin

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..")
    
from dino.generators.base import Generator, GeneratorException, GeneratorExecutionError
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
    CHAR_REGEX = re.compile('[^-A-Za-z0-9]')            

    def get_svn_uri(self, svn_uri, filepath):
        self.check_call(['svn', 'export', svn_uri, filepath])

                    
    def query_dynamic(self):
        
        sess = self.db_config.session()
        
        self.log.info("Looking for blessed interfaces")
        ports = sess.query(Port).filter_by(is_blessed=True)\
            .join(Device).join(Rack).join(Site).filter_by(name=self.settings.site).all()            
        self.log.info("Found %d blessed ports" % len(ports))
            
        for port in ports:
            self.log.fine("  Port: %s", port)
            
            if port.interface is None:
                self.log.warn("Skipping Port with no Interface: " % port)
                continue
            
            host = port.device.host
            device = port.device
            
            rec = FullARecord()
            rec.fqdn = "%s.%s.%s.%s" % (host.name, host.pod.name, host.site.name, self.settings.domain) 
            rec.ip = port.interface.address.value
            self.log.fine("    FQDN: %s", rec.fqdn)
            yield rec
            
            if port.device.hw_class == 'server':
                rec = ForwardARecord()            
                (rack_name, count) = self.CHAR_REGEX.subn('-', device.rack.name)
                if count > 0:
                	self.log.fine(" Replaced %d chars", count)  
                rec.fqdn = "slot%s.rack%s.%s.%s" % (device.rackpos, rack_name, device.site.name, self.settings.domain)
                rec.ip = port.interface.address.value
                self.log.fine("    FQDN: %s", rec.fqdn)
                yield rec

            
            
            
        self.log.info("Looking for IPMI interfaces")
        ports = sess.query(Port).filter_by(is_ipmi=True)\
            .join(Device).join(Rack).join(Site).filter_by(name=self.settings.site).all()
            
        self.log.info("Found %d ipmi ports" % len(ports))
        
        for port in ports:
            self.log.fine("  Port: %s", port)
            
            if port.interface is None:
                self.log.warn("Skipping Port with no Interface: " % port)
                continue
                
            host = port.device.host            
            #rec = FullARecord()
            rec = ForwardARecord()
            rec.fqdn = "ipmi-%s.%s.%s.%s" % (host.name, host.pod.name, host.site.name, self.settings.domain) 
            rec.ip = port.interface.address.value
            self.log.fine("    FQDN: %s", rec.fqdn)
            yield rec
            
            device = port.device
            if device.hw_class == 'server':
                rec = ForwardARecord()
                (rack_name, count) = self.CHAR_REGEX.subn('-', device.rack.name)
                if count > 0:
                	self.log.fine(" Replaced %d chars", count)  
                rec.fqdn = "ipmi-slot%s.rack%s.%s.%s" % (device.rackpos, rack_name, device.site.name, self.settings.domain)
                rec.ip = port.interface.address.value
                self.log.fine("    FQDN: %s", rec.fqdn)
                yield rec

            
        sess.close()
    
    
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
            
        self.check_duplicate_aname(static_set | dynamic_set)
        self.check_duplicate_ip(static_set | dynamic_set)
    
    def check_duplicate_aname(self, rec_set):
        duplicate = False
        xmap = {}
        for r in rec_set:
            if not isinstance(r, (FullSoaRecord, NsOnlyRecord, FullARecord, ForwardARecord, MxRecord)):
                continue
                
            if xmap.has_key(r.aname):
                duplicate = True
                self.log.warning("Duplicate Name (A record): %s", r.aname)
                self.log.warning(r)
                self.log.warning(xmap[r.aname])
                
            xmap[r.aname] = r
        
        if duplicate:
            raise GeneratorExecutionError("Duplicate Name issues")        
    
    def check_duplicate_ip(self, rec_set):
        duplicate = False
        xmap = {}
        for r in rec_set:
            if not isinstance(r, FullARecord):
                continue
            if xmap.has_key(r.ip):
                duplicate = True
                self.log.warning("Duplicate IP address: %s", r.ip)
                self.log.warning(r)
                self.log.warning(xmap[r.ip])
                
            xmap[r.ip] = r
        
        if duplicate:
            raise GeneratorExecutionError("Duplicate IP address issues")
        
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
        
        dynamic = list( self.query_dynamic() )
    
        #
        # check static and dynamic files
        #  
        self.check_sets(static_set, set(dynamic))

        #
        # Write the output file
        #        
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


    def compare(self):
        
        generated_fp = pjoin(self.workdir, self.settings.dns_combinded_file)
        active_fp = self.settings.dns_data_file

        generated_records = set(DnsRecord.parse_data_file(generated_fp))
        active_records = set(DnsRecord.parse_data_file(active_fp))
    
        rename_from_records = []
        rename_to_records = []
        for active_rec in sorted(active_records - generated_records):
            if isinstance(active_rec, FullARecord):
                for generated_rec in generated_records:
                    if isinstance(generated_rec, active_rec.__class__) and active_rec.ip == generated_rec.ip:
                        rename_from_records.append(active_rec)
                        rename_to_records.append(generated_rec)
                        continue
                    
                        
        removing_records = [ r for r in active_records - generated_records if r not in rename_from_records ]
                
        adding_records = [ r for r in generated_records - active_records if r not in rename_to_records ]
        
        if len(rename_from_records) > 0:
            for i, active_rec in enumerate(rename_from_records):
                generated_rec = rename_to_records[i]                
                self.log.info("Renaming: ")
                self.log.info("   %s ->", active_rec)
                self.log.info("   %s", generated_rec)
        
        if len(removing_records) > 0:
            self.log.info("Removing: ")
            for r in sorted(removing_records):
                self.log.info("   %s", r)
        
        if len(adding_records) > 0:           
            self.log.info("Adding: ")
            for r in sorted(adding_records):
                self.log.info("   %s", r)
                
                
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
