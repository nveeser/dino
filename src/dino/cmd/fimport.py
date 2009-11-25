#/usr/bin/env python 

import os
import types
import logging
import yaml
from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.command import *
from dino.db import *
from dino import class_logger

'''
--- 
facterversion: 1.5.7
hardwareisa: AMD Opteron(tm) Processor 254
hardwaremodel: i686
interfaces: eth0
ipaddress_eth0: 172.31.127.22
is_virtual: true
macaddress: 00:0c:29:91:14:17
macaddress_eth0: 00:0c:29:91:14:17
manufacturer: VMware, Inc.
memorysize: 2.01 GB
netmask: 255.0.0.0
netmask_eth0: 255.255.255.0
network_eth0: 172.31.127.0
physicalprocessorcount: "0"
processor0: AMD Opteron(tm) Processor 254
processorcount: "1"
productname: VMware Virtual Platform
serialnumber: VMware-56 4d 1f 79 84 37 60 4d-e8 a9 6a a4 4f 91 14 17
type: Other
virtual: vmware

---
facterversion: 1.5.7
architecture: x86_64
hardwareisa: x86_64
hardwaremodel: x86_64
hostname: repo02
interfaces: eth1,eth2,eth3
ipaddress: 172.29.5.18
ipaddress_eth1: 172.29.5.18
macaddress: 00:E0:81:47:CC:72
macaddress_eth1: 00:E0:81:47:CC:72
macaddress_eth2: 00:E0:81:47:CC:73
macaddress_eth3: 00:E0:81:47:CC:A5
manufacturer: empty
memorysize: 1.94 GB
netmask: 255.255.255.0
netmask_eth1: 255.255.255.0
network_eth1: 172.29.5.0
physicalprocessorcount: "0"
processor0: AMD Opteron(tm) Processor 252
processor1: AMD Opteron(tm) Processor 252
processorcount: "2"
productname: empty
serialnumber: empty
type: Main Server Chassis
virtual: physical

---
facterversion: 1.3.8
architecture: x86_64
hardwareisa: AMD Opteron(tm) Processor 248
hardwaremodel: x86_64
ipaddress: 172.29.4.107
ipaddress_eth1: 172.29.4.107
macaddress: 00:e0:81:40:7c:df
macaddress_eth1: 00:e0:81:40:7d:08
manufacturer: To Be Filled By O.E.M.
memorysize: 15.58 GB
processor0: AMD Opteron(tm) Processor 248
processor1: AMD Opteron(tm) Processor 248
processorcount: "2"
productname: To Be Filled By O.E.M.
serialnumber: To Be Filled By O.E.M.
virtual: physical
---
facterversion: 1.3.8

ipaddress: 172.29.4.107
macaddress: 00:e0:81:40:7c:df
ipaddress_eth1: 172.29.4.107
macaddress_eth1: 00:e0:81:40:7d:08

manufacturer: To Be Filled By O.E.M.
productname: To Be Filled By O.E.M.
serialnumber: To Be Filled By O.E.M.
virtual: physical

architecture: x86_64
hardwareisa: AMD Opteron(tm) Processor 248
hardwaremodel: x86_64

memorysize: 15.58 GB
processor0: AMD Opteron(tm) Processor 248
processor1: AMD Opteron(tm) Processor 248
processorcount: "2"

---
architecture => x86_64
cdp_device_eth0 => a5s1
cdp_port_eth0 => GigabitEthernet1/3
dmidecode_bios_vendor => Dell Inc.
dmidecode_chassis_type => Rack Mount Chassis
dmidecode_ipmi_spec_version => 2.0
facterversion => 1.5.5
hardwareisa => x86_64
hardwaremodel => x86_64
interfaces => eth0,eth1,eth2,eth3,sit0
ipaddress => 172.29.5.17
ipaddress_eth0 => 172.29.5.17
ipmi_device => true
ipmi_gateway1 => 172.29.5.1
ipmi_gateway2 => 0.0.0.0
ipmi_ip => 172.29.5.27
ipmi_mac => 00:26:b9:33:25:d9
ipmi_mask => 255.255.255.0
is_virtual => false
macaddress => 00:26:B9:33:25:D1
macaddress_eth0 => 00:26:B9:33:25:D1
macaddress_eth1 => 00:26:B9:33:25:D3
macaddress_eth2 => 00:26:B9:33:25:D5
macaddress_eth3 => 00:26:B9:33:25:D7
manufacturer => Dell Inc.
memorysize => 93.67 GB
netmask => 255.255.255.0
netmask_eth0 => 255.255.255.0
network_eth0 => 172.29.5.0
physicalprocessorcount => 2
processor0 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor1 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor10 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor11 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor12 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor13 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor14 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor15 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor2 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor3 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor4 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor5 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor6 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor7 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor8 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processor9 => Intel(R) Xeon(R) CPU           X5550  @ 2.67GHz
processorcount => 16
productname => PowerEdge R710
serialnumber => 8V4LVH1
type => Rack Mount Chassis
virtual => physical

'''


class FacterProcessorError(Exception):
    pass

class MissingChassisError(FacterProcessorError):
    def __init__(self, manufacturer, productname):
        self.manufacturer = manufacturer
        self.productname = productname

BAD_SERIALNO_LIST = ('empty', '1234567890', 'To Be Filled By O.E.M.')


class FacterImportCommand(DinoCommand):

    NAME = 'fimport'
    USAGE = 'file'
    GROUP = 'data'
    OPTIONS = (
         Option('-n', '--no-submit', action='store_false', dest='submit', default=True),
    )

    def validate(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, "Must specify a file/dir to add")


    @with_session
    def execute(self, opts, args, session):

        proc = FacterInfoProcessor(session)

        session.open_changeset()
        try:
            for d in self.arg_iterator(args):
                for data_dict in d:
                    proc.process(data_dict)

        except FacterProcessorError, e:
            raise CommandExecutionError(self, e)

        desc = session.create_change_description()

        if len(desc) > 0:
            self.log.info("Changes:")
            for change in desc:
                self.log.info("  " + str(change))

        if opts.submit:
            self.log.fine("Submitting Objects: %s / %s " % (len(session.new), len(session.dirty)))
            cs = session.submit_changeset()
            self.log.info("Committed Changeset: " + str(cs))

        else:
            session.revert_changeset()
            self.log.info("Not submitting")




    def arg_iterator(self, args):
        ''' look through args and produce a list (tuple, generator) of dictionaries '''

        def yaml_data(filepath):
            f = open(filepath)
            text = f.read()
            f.close()
            return yaml.load_all(text)

        for arg in args:
            if not os.path.exists(arg):
                raise CommandArgumentError(self, "Path does not exist: " + arg)

            if os.path.isfile(arg):
                yield yaml_data(arg)

            elif os.path.isdir(arg):
                for x in os.listdir(arg):
                    filepath = os.path.join(arg, x)
                    if os.path.isfile(filepath):
                        yield yaml_data(filepath)

            else:
                raise CommandArgumentError(self, "add can only accept dir or file")



class FacterInfoProcessor(object):
    def __init__(self, session):
        self.session = session

    def process(self, data_dict):
        if not isinstance(data_dict, dict):
             raise FacterProcessorError("Invalid type passed in: %s" % type(data))

        # Device 
        #
        device = self.find_device(data_dict)
        if device is None:
            hid = self.create_hid(data_dict)
            serialno = data_dict.get('serialnumber')
            device = Device(hid=hid, status="INVENTORY", serialno=serialno)
            self.session.add(device)

        # Physical / Virtual
        if data_dict.get('virtual', 'physical') == 'physical':
            hw_type = 'server'
        else:
            hw_type = 'vm'

        self.log.info("Server type: %s", hw_type)

        device.hw_type = hw_type

        # Chassis
        #
        if device.chassis is None:
            vendor = data_dict.get('manufacturer')
            product = data_dict.get('productname')

            if vendor == 'empty' and product == 'empty':
                vendor = data_dict.get('baseboard_manufacturer')
                product = data_dict.get('baseboard_model')

            device.chassis = self.session.query(Chassis).filter_by(vendor=vendor, product=product).first()

            if device.chassis is None:
                raise FacterProcessorError("Could not find chassis information from data: (manufacturer/productname) %s/%s" % (vendor, product))

        # Host
        # 
        if device.host is None:
            pod = self.session.query(Pod).filter_by(name='inv').first()
            name = "%s-%s" % (device.chassis.name, device.hid)
            device.host = Host(name=name, pod=pod)

        # Ports / Interfaces
        #
        network = self.update_port_info(device, data_dict)

        # Rack
        #
        device.rack = self.find_rack(network)

        # IPMI
        #
        self.update_ipmi(device, data_dict)

        # Network info
        #
        self.update_switch(device, data_dict)


    def update_switch(self, device, data_dict):
        '''
        cdp_device_eth0: a2s1.sjc1.metaweb.com
        cdp_port_eth0: GigabitEthernet1/1
        '''

        port = device.blessed_port()

        switch_name = data_dict.get('cdp_device_%s' % port.name)
        port_name = data_dict.get('cdp_port_%s' % port.name)

        switch = self._find_switch(switch_name)

        if switch is None:
            return

        device.switch = switch
        device.switch_port = port_name

    def _find_switch(self, name):
        self.log.info("Find Switch: %s", name)
        device = self.session.query(Device).filter_by(hw_class='switch').join(Host).filter(Host.name == name).first()
        if device:
            return device

        parts = name.split('.')
        name = parts[0]

        self.log.info("Find Switch: %s", name)
        device = self.session.query(Device).filter_by(hw_class='switch').join(Host).filter_by(name=name).join(Pod).first()
        if device:
            return device

        return None

    def find_device(self, data_dict):
        device = None

        serialnum = self.get_serial(data_dict)
        if serialnum is not None:
            self.log.fine("FindDev: by SerialNumber: %s", serialnum)
            device = self.session.query(Device).filter_by(instance_name=serialnum).first()

            if device:
                self.log.info("Found Device: %s", str(device))
                return device

        interfaces = data_dict.get('interfaces')
        if interfaces is None:
            raise FacterProcessorError("Facter data does not provide interfaces list")

        for iface in interfaces.split(','):
            self.log.info("FindDev: by Interface: %s", iface)

            if not data_dict.has_key("macaddress_%s" % iface):
                continue

            macname = data_dict.get("macaddress_%s" % iface).replace(":", "")

            device = self.session.query(Device).filter_by(instance_name=macname).first()
            if device:
                return device

        return None


    def create_hid(self, data_dict):
        serial = self.get_serial(data_dict)

        if serial is not None and serial not in BAD_SERIALNO_LIST:
            return serial

        interfaces = data_dict.get('interfaces')
        if interfaces is None:
            raise FacterProcessorError("Facter data does not provide interfaces list")

        for iface in interfaces.split(','):
            if data_dict.has_key("macaddress_%s" % iface):
                return data_dict.get("macaddress_%s" % iface).replace(":", "")

        raise FacterProcessorError("Could not find serial number or mac address")


    def update_port_info(self, device, data_dict):
        found_ports = []
        blessed_address = None
        for iface_name in data_dict.get('interfaces', "").split(","):
            mac = data_dict['macaddress_%s' % iface_name]
            port = device.find_port(mac)

            if port is None:
                port = Port(mac=mac, name=iface_name, device=device)
                self.log.info("NEW Port: %s", port)

            found_ports.append(port)

            if data_dict.has_key("ipaddress_%s" % iface_name):
                self.log.info("Port has blessed addres: %s" % port)
                port.is_blessed = True

                if port.interface is None:
                    self.session.add(Interface(port_name=iface_name, host=device.host))

                ipvalue = data_dict["ipaddress_%s" % iface_name]
                blessed_address = IpAddress(value=ipvalue)
                if blessed_address != port.interface.address:
                    self.log.info("setting port to blessed address")
                    port.interface.address = blessed_address
                else:
                    self.log.info("getting blessed address from port")
                    blessed_address = port.interface.address


        # remove ports that no longer show up in the probe
        for port in device.ports:
            if port not in found_ports and not port.is_ipmi:
                device.ports.remove(port)

        if blessed_address is None:
            raise FacterProcessorError("Could not find the blessed address")

        self.log.info("Blessed Address: %s", blessed_address)
        return blessed_address.query_subnet()


    def find_rack(self, network):
        # Rack / Site
        # 
        if network.site is None:
            raise FacterProcessorError("Subnet does not have a (single) site: %s" % network)

        # Find the rack from the site
        rack = self.session.query(Rack).filter_by(name='UNKNOWN').filter_by(site=network.site).first()

        if rack is None:
            raise FacterProcessorError("Could not find the UNKNOWN rack for site: %s" % network.site)
        return rack


    def get_serial(self, data_dict):
        serial = data_dict.get('serialnumber')

        if serial is not None:
            serial = serial.replace(" ", "")
            serial = serial.replace("VMware-", "")

        return serial


    def update_ipmi(self, device, data_dict):

        if not bool(data_dict.get('ipmi_device')):
            return

        self.log.fine("Found IPMI info")
        mac = data_dict.get('ipmi_mac')
        if mac is None:
            raise FacterProcessorError("ipmi_device is true but ipmi_mac is not set")


        port = device.find_port(mac)
        if port is None:
            port = Port(mac=mac, name="ipmi", device=device, is_ipmi=True)
            self.log.info("NEW IPMI Port: %s", port)

        if data_dict.get('ipmi_ip'):
            if port.interface is None:
                self.session.add(Interface(port_name="ipmi", host=device.host))

            ipvalue = data_dict.get('ipmi_ip')
            addr = IpAddress(value=ipvalue)
            if port.interface.address != addr:
                port.interface.address = addr



class_logger(FacterInfoProcessor)





