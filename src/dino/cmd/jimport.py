#/usr/bin/env python

import os
import logging
try:
    import json
except ImportError:
    import simplejson as json

from optparse import Option

from itertools import ifilter

from dino.cmd.command import with_session, DinoCommand
from dino.cmd.exception import *
from dino.db import *

"""
  JSON Import Format: Version 0  

  "hdd.controller_dict": "MegaRAID SAS",
  "hdd.hdtype_dict": "ST3750640NS",
  "hdd_total": "2",
  "hnode.coreswitch": "A",
  "hnode.handle": "index03.p01.sjc1.metaweb.com",
  "hnode.loc_rack": "9",
  "hnode.loc_rackpos": "19",
  "hnode.loc_row": "1",
  "hnode.mw_tag": "1",
  "hnode.os_id": "baccus",
  
  "hnode.pdu_port": "AB7",
  "hnode.serialno": "..CN7082184700NR.",
  "hnode.status": "ACTIVE",
  "hnode.type_dict": "idx-1",

  "appliance.name": "baccus-prod",
  "blessed_port": "eth0",
  "model.name": "util",
  "site.domain": "sjc1",
  "pod.domain": "p01",
  
  "mac_port.mac eth0": "00:1E:C9:43:AD:83",
  "mac_port.mac eth1": "00:1E:C9:43:AD:84",
  "mac_port.mac ipmi": "00:1E:C9:43:AD:87",
  "mac_port.s_port": "1/19",
  "mac_port.vlan": "9",
  
  "ip_mac.addr eth0": "10.2.9.31",
  "ip_mac.addr ipmi": "10.2.9.32",

  
  "name_ip.name blessed": "index03.p01.sjc1.metaweb.com",
  "name_ip.name iloc": "ipmi-slot19.rack9.sjc1.metaweb.com",
  "name_ip.name ipmi": "ipmi-index03.p01.sjc1.metaweb.com",
  "name_ip.name loc": "slot19.rack9.sjc1.metaweb.com",
  
  "switch_handle": "a9s1.net.sjc1.metaweb.com"
  
  "rapids.bootimg": "pxelinux.0",
  "rapids.build_tag": "baccus-postgis",
  "rapids.build_type": "physical",
  "rapids.rapids_ver": "3",
  """



class JsonImportCommand(DinoCommand):
    ''' 
    (This command is currently unused)
    '''

    NAME = 'jimport'
    USAGE = '<file|dir> [ , <file|dir> ] ... ]'
    GROUP = "data"
    OPTIONS = (
        Option('-n', '--no-submit', action='store_false', dest='submit', default=True),
    )

    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specify a file/dir to add")


    @with_session
    def execute(self, session):
        if self.cmd_env:
            self.cmd_env.increase_verbose()

        proc = BasicJsonProcessor(self, session)

        for path in self.arg_iterator():
            session.open_changeset()

            proc.process(path)

            if self.option.submit:
                self.log.fine("Submitting Objects: %s / %s " % (len(session.new), len(session.dirty)))
                cs = session.submit_changeset()
                self.log.info("Committed Changeset: " + str(cs))

            else:
                session.revert_changeset()
                self.log.info("Not submitting")



        if self.cmd_env and len(proc.unknown_items) > 0:
            self.log.error("Missing items:")
            for name, value in proc.unknown_items:
                self.log.error("    %s: %s", name, value)



    def arg_iterator(self):
        for path in self.args:
            if not os.path.exists(path):
                raise CommandArgumentError(self, "Path does not exist: " + path)

            if os.path.isfile(path):
                yield path

            elif os.path.isdir(path):
                for x in os.listdir(path):
                    filepath = os.path.join(path, x)
                    if os.path.isfile(filepath):
                        yield filepath

            else:
                raise CommandArgumentError(self, "add can only accept dir or file")





class BasicJsonProcessor(object):
    log = logging.getLogger("dino.cmd.import")

    def __init__(self, cmd, session):
        self.cmd = cmd
        self.session = session
        self.unknown_items = set()

        self._init_cache()

    def _init_cache(self):
        self.cache = {
        'device' : None,
        'blessed_port' : None,
        'ipmi_iface' : None,
        'ports' : {},
        'addrs' : {},
        }


    def process(self, filepath):
        self.log.info("Processing: %s", filepath)
        self._init_cache()
        data = json.load(open(filepath))

        for k, v in data.iteritems():
            if v == "None":
                data[k] = None

        self._upsert_device(data)
        self._upsert_host(data)
        self._upsert_port_interface(data)
        self._upsert_addresses(data)



    def _upsert_device(self, data):
        '''
        "blessed_port": "eth0",
        "mac_port.mac eth0": "00:1E:C9:43:AD:83",
        "hnode.pdu_port": "AB7",
        "hnode.serialno": "..CN7082184700NR.",
        "hnode.status": "ACTIVE",
        "hnode.type_dict": "idx-1",          
        "hnode.loc_rackpos": "19",
        
        "hnode.loc_rack": "9",
        "hnode.loc_row": "1",        
        "site.domain": "sjc1",
         "model.name": "util",
        '''


        port = data['blessed_port']
        hid = data['mac_port.mac %s' % port].replace(":", "")

        device = self.session.query(Device).filter_by(hid=hid).first()
        if device is None:
            device = Device(hid=hid)
            self.log.info("  Adding(dev): %s" % device)
            self.session.add(device)
        else:
            self.log.info("  Updating: %s" % device)

        self.cache['device'] = device


        # 
        # Attributes
        #
        device.hw_type = data.get('hnode.type_dict', None)
        device.pdu_port = data.get('hnode.pdu_port', None)
        device.serialno = data.get('hnode.serialno', None)
        device.status = data.get('hnode.status', None)
        device.rackpos = data.get('hnode.loc_rackpos', None)


        #
        # Rack
        #
        if data['hnode.loc_row'] is None and data['hnode.loc_rack'] is None:
            rack_name = "unknown"
        else:
            rack_name = "%s.%s" % (data['hnode.loc_row'], data['hnode.loc_rack'])
        device.rack = self.session.query(Rack).filter_by(name=rack_name).first()
        if device.rack is None:
            raise CommandExecutionError(self.cmd, "Cannot add device: Unknown rack: %s" % rack_name)

        #
        # Site
        #
        device.rack.site = self.session.query(Site).filter_by(name=data['site.domain']).first()
        if  device.rack.site is None:
            self.log.error("Unknown Site: " + data['site.domain'])
            raise CommandExecutionError(self.cmd, "Cannot add device: Unknown site: %s" % data['site.domain'])

        #
        # Chassis
        #
        device.chassis = self.session.query(Chassis).filter_by(name=data['model.name']).first()
        if device.chassis is None:
            self.log.warn("Unknown Chassis: " + data['model.name'])
            self.unknown_items.add(('Chassis', data['model.name']))


    def _upsert_host(self, data):
        '''
          "pod.domain": "p01",
          "appliance.name": "baccus-prod",
          "hnode.os_id": "baccus",
          "hnode.handle": "index03.p01.sjc1.metaweb.com",
          "hnode.loc_row": "1",

        '''

        #
        # Find host
        #
        pod = self.session.query(Pod).filter_by(name=data['pod.domain']).first()
        if pod is None:
            self.log.error("Unknown Pod: %s" % data['pod.domain'])
            raise CommandExecutionError(self.cmd, "Cannot add host: Unknown pod: %s" % data['pod.domain'])


        # 
        # Find Appliance
        #
        appliance_name = data['appliance.name']
        os_name = data['hnode.os_id']

        appliance = self.session.query(Appliance).join(OperatingSystem).\
            filter(Appliance.name == appliance_name).\
            filter(OperatingSystem.name == os_name).first()

        if appliance is None:
            self.log.warn("Unknown OS/Appliance: %s/%s" % (os_name, appliance_name))
            self.unknown_items.add(('Appliance', "%s/%s" % (os_name, appliance_name)))


        # 
        # Find Host
        #
        name = data['hnode.handle'].split('.')[0]
        site = self.cache['device'].rack.site
        host = self.session.query(Host).filter_by(name=name, pod=pod)\
            .join(Device).join(Rack).filter_by(site=site).first()


        if host is None:
            try:
                hnode_id = int(data['hnode.mw_tag'])
            except TypeError:
                hnode_id = None

            host = Host(id=hnode_id, name=name, pod=pod, appliance=appliance)
            self.session.add(host)

            self.cache['device'].host = host
            self.log.info("  Adding(h): %s" % host)

        elif self.cache['device'].host != host:
            raise CommandExecutionError("Device / Host do not match during import: %s %s" % (self.cache['device'], host))

        else:
            host.pod = pod
            host.appliance = appliance
            self.log.info("  Updating: %s" % host)

        self.cache['host'] = host


    def _upsert_port_interface(self, data):
        '''
          "mac_port.mac eth0": "00:1E:C9:43:AD:83",
          "mac_port.mac eth1": "00:1E:C9:43:AD:84",
          "mac_port.mac ipmi": "00:1E:C9:43:AD:87",
          "blessed_port": "eth0",
          "mac_port.vlan": "9",
          '''

        probed_ports = []

        for key in ifilter(lambda x: x.startswith('mac_port'), sorted(data.keys())):

            if key == 'mac_port.s_port':
                continue

            if key.startswith('mac_port.mac'):
                (x, ifname) = key.split()
                mac = data[key]

                port = self.session.query(Port).filter_by(mac=mac).first()
                if port is None:
                    port = Port(name=ifname, mac=mac, device=self.cache['device'])
                    self.log.fine("  Adding(port): %s" % port)
                else:
                    self.log.fine("  Updating: %s" % port)

                probed_ports.append(port)

                self.cache['ports'][ifname] = port

                if ifname == 'ipmi':
                    port.is_ipmi = True
                    self.cache['ipmi_iface'] = port.interface

                if ifname == data['blessed_port']:
                    port.is_blessed = True
                    self.cache['blessed_port'] = port

        if self.cache['blessed_port'] and data['mac_port.vlan'] != "":
            self.cache['blessed_port'].vlan = int(data['mac_port.vlan'])

        # remove ports in db no longer in use
        for port in self.cache['device'].ports:
            if port not in probed_ports:
                self.log.fine("  Removing Port: %s" % port)
                self.cache['device'].ports.remove(port)

    def _upsert_addresses(self, data):
        '''                  
          "ip_mac.addr eth0": "10.2.9.31",
          "ip_mac.addr ipmi": "10.2.9.32",
        '''

        for key in ifilter(lambda x: x.startswith('ip_mac.addr'), sorted(data.keys())):
            (x, ifname) = key.split()

            if ifname == "blessed":
                if not self.cache['blessed_port']:
                    raise CommandExecutionError("Blessed port unspecifed, but used by key: %s" % key)

                ifname = self.cache['blessed_port'].name

            port = self.cache['ports'][ifname]
            if not port.interface:
                self.cache['host'].interfaces.append(Interface(port_name=port.name))

            ip = self.session.query(IpAddress).filter_by(value=data[key]).first()

            if ip is None:
                ip = IpAddress(value=data[key], interface=port.interface)
                ip.subnet = ip.query_subnet()
                self.log.fine("  Adding(ip): %s" % ip)
                self.session.add(ip)

            elif ip.interface is None:
                self.log.warning("   IpAddress instance has no interface: %s" % ip)
                ip.interface = port.interface

            elif ip.interface.port is not None and ip.interface.port != port:
                    raise CommandExecutionError("Ip Address currenty in Use: %s -> %s" % (ip, ip.interface.port))

            else:
                self.log.fine("  Updating %s" % ip)

            self.cache['addrs'][ifname] = ip


































