#!/usr/bin/env python
"""
Rapids generator

this is the core generator functionality for converting dino generated json
into yaml which rapids can operate upon.
"""

import sys
import copy
import os
from os.path import join as pjoin
import yaml
from optparse import Option

from dino.generators.base import Generator, GeneratorExecutionError
from dino.db import (Device, Rack, Site, Host, IpType)


HID_JSON_PATTERN = 'hostid-%i.json'
HID_YAML_PATTERN = 'hostid-%i'


'''
{ "fqdn": "hadoop0002.inv.sjc1.metaweb.com",
  "gentoo_version": "2007.0",
  "host": "hadoop0002.inv.sjc1.metaweb.com",
  "host_no": 12,
  "inherit": { "appliance": "baccus-hadoop",
               "datacenter": "sjc1",
               "pod": "inv.sjc1"},
               
  "nic": { "0": [ { "bc": "172.29.1.255",
                    "gw": "172.29.1.1",
                    "ip": "172.29.1.13",
                    "nm": "255.255.255.0"}],
           "ipmi": [ { "bc": "172.29.1.255",
                       "gw": "172.29.1.1",
                       "ip": "172.29.1.14",
                       "nm": "255.255.255.0"}]},
  "os_codename": "baccus",
  "portage": "20071217",
  "release_proto": "svn-https",
  "release_source": "svn.metaweb.com/svn/rapids/tags/build/",
  "tmpl_data": { "ssh-dsa-key": "-----BEGIN DSA PRIVATE KEY-----\nMIIBugIBAAKBgQCD7vxAUeE9YttkrSPs4fBmJUTTEsg8Rxub2TFunom5xd5lGNOf\n90OjpWFetb9wxM7k/XynHaUdZMGBUV8eFXuCxLpQf9sl7pp0Jz1pnolDBWUulluF\nrODPoBZ69WCegOgU+/QINAPdwqXEMs1zm53Rxl3/vncnS50PoHP0Zc7PGQIVAP+2\nPLuRFHk5Dm9MbnXeM6f9ko4RAoGAVL/PpBXlfz7SsUVOTWTOlr2HZLfq12gH8hbq\nby7Bn4xf5uEPGcyYUuExcqMZmYUpn+O8b2LmQNlE1sgqfGUDqy0ocA3DB7tyirLk\naf6mLqOPfn3aXk+Ecq9r3v1sCQ7ek8Sk/kkXwNAHKDCp+lzSOaxo1c5PgsvRRQLO\ndTtSvZACgYAkDdcOrEa/fEd338rSqs7C+6M67TBFrEJQxe/mvcxCvUQdm97evvRu\nk5kfDxamYYOOtdIjAUqEVc9lHajdKD+SqYPfixlsbbMHGd5t5aEmkrWb0BwPsIId\n0SPH6SYamwQ18ZLENaP1iyzly0QnryyO7i/VL0koczvIn6vQ6p0pLwIUSN6ZUCal\nKLY8Zyty0Nftl1NJkWM=\n-----END DSA PRIVATE KEY-----\n",
                 "ssh-dsa-pub": "ssh-dss AAAAB3NzaC1kc3MAAACBAIPu/EBR4T1i22StI+zh8GYlRNMSyDxHG5vZMW6eibnF3mUY05/3Q6OlYV61v3DEzuT9fKcdpR1kwYFRXx4Ve4LEulB/2yXumnQnPWmeiUMFZS6WW4Ws4M+gFnr1YJ6A6BT79Ag0A93CpcQyzXObndHGXf++dydLnQ+gc/Rlzs8ZAAAAFQD/tjy7kRR5OQ5vTG513jOn/ZKOEQAAAIBUv8+kFeV/PtKxRU5NZM6WvYdkt+rXaAfyFupvLsGfjF/m4Q8ZzJhS4TFyoxmZhSmf47xvYuZA2UTWyCp8ZQOrLShwDcMHu3KKsuRp/qYuo49+fdpeT4Ryr2ve/WwJDt6TxKT+SRfA0AcoMKn6XNI5rGjVzk+Cy9FFAs51O1K9kAAAAIAkDdcOrEa/fEd338rSqs7C+6M67TBFrEJQxe/mvcxCvUQdm97evvRuk5kfDxamYYOOtdIjAUqEVc9lHajdKD+SqYPfixlsbbMHGd5t5aEmkrWb0BwPsIId0SPH6SYamwQ18ZLENaP1iyzly0QnryyO7i/VL0koczvIn6vQ6p0pLw== Host Key\n",
                 "ssh-rsa-key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEoQIBAAKCAQEAsSciNKo2E4jl6G+dy7KBIZHx/nQ6bzqbBBt5hBGYv+f1BmmE\n1edD9RdVcF/Gsef8jGOaHpPNXfHTlFyiEw+LsBPojFj9ch8hSJpH9cQxwvjajYof\nx7MJWZn+SgHGCsDb+qu4od8sS+cMQ7jYFEUYr59PdwqUw2pxqCOZodKlYpoD0nhY\nwdh1z/dFoEcMdD5sGQ8Ym4Sa6NeSpbHlEOujYXkxYnvXt/WApZFsJ+AH7tJbaE2a\nUxBcQTq/bJenWoiafz4F9uuOeaVdujm5POoyfhw7jbwjzxjF/HHGFofb4D1654EU\n4UmkuOsD1WStEOTyUPLPJiLVqxv6cxEWTC3/qQIBIwKCAQAtjbhWr2z9tXzyoFvG\nqj52WLqR4197r/v5vewMBIZdO6VoDIE+UWk/BgAG9A6FhMvplfRuQ0Nv7boQNRO7\nwis759y2YAaoUSXQ1zcTT7UGP/2vXggsCXduz9OsoV7PkK2YOskTrmp56vSGcVwi\neCrrVNnraR7wa9QVSvueo+FifvKGbFbc29HYf5EtWIbYualtvHhUtjXNHkwns8B+\nMKleXtguNKNSvYZulua08z59hE7BqzcB/Da5wtKAXMk/o5+VqFRPH1Z2igXgYf+w\nUNFwwDh2RWwDl85dJPeTLTBvF0fnXhkF8aP1Wb0fwEktMZtSCXMxTVO7kSaiF6F6\nc7ELAoGBANlJcbDnJ+A5x6xxKHmHAR2n5xya0x9slEiBCR1PfSWgVcqFJWUIf6w7\nzNTGmI2fZSJrEzGz/CNUVztTW5V1kcfjCl9qRz0sClfcGvhBcGpGJxChyTWyRbFr\nxOwnqsNC+U2lv5VgNkQXpe3A6mV1OJji4Swbh/36sSTO0DqBQOhxAoGBANC3KHJ/\ny4H26iu3qdvbTtf/Swua0HFelJPDJqJIeFzgXTqbbUzfeFfYJGuFI8AuarFhZ68l\nlLlv0W3tKJF7s2YA3eznKnLV9At1hTP4eGDW0MEgAWaAoSrtjt5Au5UmIodoqOVN\nhBvnIP21cg6WlhnZs/+Dw3WeGeoRcy7uuWa5AoGBAMapjIR7kiwXkfy/OvLEk05Q\nXkYJ5ZkS0LdRZ2tBXHosMS4wlzfNQYeHIayYUPaDGqMgEYyHTO0Z6VrP3rSIv8yy\nUqBhKzCdS0kDwOL6AGEqMlhZZ4GNDIT00UzxESeNsLwFQXKhG6v4XTElaJdGmiVh\nt+3QB06cD6yf1FK/UUmLAoGAEePQRFQYwf84pKlXs8JXNxXh3GxbAmcxTn5xBph/\nWGsArUCFtiHIfI7ejN+GuLOFfOsXhAqJFzV4WeEgvANJ5Cv1w9lMyAO11RizpV5w\nt9fmAezM64deRYITj2SiXT3IcgGoE6eO+xPPoLfH8p8xb+4WviE8o653P/Ld/LVg\nWUMCgYBvvbmzd3XkRfIJXTvCGpq/6vXxQfHIqBmzXzrvW0hm+j0hiBp+7RpxPy7T\nrA7vrADzmEbDuojzJfokEgvRv68+hHYqlgU+leUmzvfQ4w92FjlPugj1Z/YjzD0p\nEf4O4Sf3fz+SvGoCe4I2prMyjO8b/Qq4QxGp1VxV/155ikrb7Q==\n-----END RSA PRIVATE KEY-----\n",
                 "ssh-rsa-pub": "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAsSciNKo2E4jl6G+dy7KBIZHx/nQ6bzqbBBt5hBGYv+f1BmmE1edD9RdVcF/Gsef8jGOaHpPNXfHTlFyiEw+LsBPojFj9ch8hSJpH9cQxwvjajYofx7MJWZn+SgHGCsDb+qu4od8sS+cMQ7jYFEUYr59PdwqUw2pxqCOZodKlYpoD0nhYwdh1z/dFoEcMdD5sGQ8Ym4Sa6NeSpbHlEOujYXkxYnvXt/WApZFsJ+AH7tJbaE2aUxBcQTq/bJenWoiafz4F9uuOeaVdujm5POoyfhw7jbwjzxjF/HHGFofb4D1654EU4UmkuOsD1WStEOTyUPLPJiLVqxv6cxEWTC3/qQ== Host Key\n"}}

'''

data_base = {
    'fqdn' : None,
    'host' : None,
    'host_no' : None,
    
    'inherit' : {
        'appliance': None,
        'datacenter': None,
        'pod': None,
    },
    'nic' : {
    },
    
    'os_codename' : None,
    'release' : None,
    'portage' : None,
    'gentoo_version' : None,    
    'release_proto' : None,
    'release_source' : None, 
    
    'tmpl_data' : {
        'ssh-dsa-pub' : None, 
        'ssh-dsa-key' : None,
        'ssh-rsa-pub' : None, 
        'ssh-rsa-key' : None,
        
    },        
}



class RapidsGenerator(Generator):
    NAME = "rapids"
    OPTIONS = (
        Option('-i', '--id', type="int", dest="hostid", default=None),
    )
    
    def query(self):
        session = self.db_config.session()
        
        for host in session.query(Host)\
            .join(Device).filter_by(hw_class='server')\
            .join(Rack).join(Site).filter_by(name=self.settings.site).all():
            
            self.log.fine("Process Host: %s", host)
            d = copy.deepcopy(data_base)
            d['host_no'] = host.id
            d['fqdn'] = d['host'] = host.hostname() + "." + self.settings.domain
            d['release_proto'] = 'svn-https'
            d['release_source'] = self.settings.rapids_svn_path + host.appliance.os.name

            d['inherit']['appliance'] = host.appliance.name            
            d['inherit']['datacenter'] = host.device.rack.site.name
            d['inherit']['pod'] = host.pod.name + '.' + host.device.rack.site.name
            if int(self.settings.rapids_force_stage_inherit):
                d['inherit']['stage-definitions'] = 'default'
            d['inherit']['host'] = d['host']

            d['os_codename'] = host.appliance.os.name
            d['portage'] = host.appliance.os.name
            d['gentoo_version'] = host.appliance.os.name
            d['release'] = host.appliance.os.name
            
            if host.ssh_key_info is None:
                self.log.error("  Skipping host: %s: No ssh keys", str(host))
                continue
            
            d['tmpl_data']['ssh-rsa-key'] = host.ssh_key_info.rsa_key
            d['tmpl_data']['ssh-rsa-pub'] = host.ssh_key_info.rsa_pub
            d['tmpl_data']['ssh-dsa-key'] = host.ssh_key_info.dsa_key
            d['tmpl_data']['ssh-dsa-pub'] = host.ssh_key_info.dsa_pub

            for p in host.device.ports:
                if not p.interface:
                    continue
                    
                name = p.interface.name()                
                if name.startswith('eth'):
                    name = int(name[3])
                        
                if p.interface.address is None:
                    self.log.error("Inteface have no Address: %s", p.interface)
                    continue
                
                if p.interface.address.subnet is None:
                    raise GeneratorExecutionError("Address has no Subnet: %s" % p.interface.address)
                    
                d['nic'][name] = {}
                d['nic'][name]['ip'] = p.interface.address.value
                d['nic'][name]['gw'] = IpType.ntoa(p.interface.address.subnet.naddr + p.interface.address.subnet.gateway)
                d['nic'][name]['nm'] = p.interface.address.subnet.mask
                d['nic'][name]['bc'] = IpType.ntoa(p.interface.address.subnet.broadcast)
            
#            if d['nic'][0]['ip'] is None:
#                raise GeneratorExecutionError("Host has no blessed interface: %s" % host)
            
            yield d 
            
        session.close()
        
    def generate(self):
        self.setup_dir(self.workdir)
        
        self.log.info("generate rapids for datacenter %s", self.settings.site)
        for d in self.query():
            hid = d['host_no']

            self.log.fine("updating hid %i", hid)
            
            filename = pjoin(self.workdir, HID_YAML_PATTERN % hid)
        
            self.log.fine("   state file: %s", filename)                    

            f = open(filename, 'w')
            yaml.safe_dump(d, stream=f)
            f.close()
            
            self.log.finer("finished dumping yaml for %i", hid)
                    
        self.log.info("completed")
        
        
        
    def activate(self):        
        
        state_dir = self.settings.rapids_state_dir
        if state_dir is None:
            state_dir = pjoin(self.settings.rapids_root, 'state')
            
        if self.option.hostid is not None:
            filenames = [ HID_YAML_PATTERN % self.option.hostid ]
        else:
            filenames = os.listdir(self.workdir)

            
        for filename in filenames:
            self.log.fine('activating: %s', filename)
                     
            f = open(pjoin(self.workdir, filename), 'r')
            data = f.read()
            f.close()
                       
            f = open(pjoin(state_dir, filename), 'w')
            f.write(data)
            f.close()

            #self.log.info('activate: updating: %s', filename)



if __name__ == '__main__':
    RapidsGenerator.main()
