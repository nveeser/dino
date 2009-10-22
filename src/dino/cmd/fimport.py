#/usr/bin/env python

import os
import logging
import yaml
from optparse import Option

from dino.cmd.maincmd import MainCommand
from dino.cmd.command import with_session
from dino.cmd.exception import *
from dino.db import *
from dino.config import class_logger

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


'''
class FacterProcessorError(Exception):
	pass

BAD_SERIAL_LIST = ('empty', '1234567890', 'To Be Filled By O.E.M.')

class FacterInfoProcessor(object):
	def __init__(self, session):
		self.session = session


	def process(self, data):
		if isinstance(data, basestring):
			data = yaml.load_all(data)
		elif isinstance(data, dict):
			pass
		else:
			raise FacterProcessorError("Invalid type passed in: %s" % type(data))

		device = self.find_device(data)

		if device is None:
			hid = self.create_hid(data)
			device = Device(hid=hid, status="INVENTORY")
			self.session.add(device)
			device.host = Host()


		if data.get('virtual', 'physical') == 'physical':
			device.hw_type = 'server'
		else:
			device.hw_type = 'vm'
		self.log.info("Server type: %s", device.hw_type)

		device.serialno = data.get('serialnumber')

		found_ports = []
		ipaddress = None
		for iface in data.get('interfaces', "").split(","):
			mac = data['macaddress_%s' % iface]
			port = device.find_port(mac)
			if port is None:
				port = Port(mac=mac, name=iface, device=device)

			self.log.info("Port: %s", port)

			found_ports.append(port)

			if data.has_key("ipaddress_%s" % iface):
				port.is_blessed = True
				ipvalue = data["ipaddress_%s" % iface]
				ipaddress = IpAddress(value=ipvalue)
				iface = Interface(port_name=port.name, host=device.host, address=ipaddress)
				self.session.add(ipaddress)
				self.session.add(iface)

		# remove ports that no longer show up in the probe
		for port in device.ports:
			if port not in found_ports:
				device.ports.remove(port)


		# Find the site from the subnet
		net = ipaddress.query_subnet()
		ipaddress.subnet = net

		self.log.info("%s -> %s", ipaddress, net)

		if net.site is None:
			raise FacterProcessorError("Subnet does not have a (single) site: %s" % net)

		# Find the rack from the site
		rack = self.session.query(Rack).filter_by(name='UNKNOWN').filter_by(site=net.site).first()

		if rack is None:
			raise FacterProcessorError("Could not find the UNKNOWN rack for site: %s" % net.site)

		device.rack = rack






	def create_hid(self, data):
		hid = data.get('serialnumber')

		if hid is not None and hid not in BAD_SERIAL_LIST:
			return hid

		interfaces = data.get('interfaces')
		if interfaces is None:
			raise FacterProcessorError("Facter data does not provide interfaces list")

		for iface in interfaces.split(','):
			if data.has_key("macaddress_%s" % iface):
				return data.get("macaddress_%s" % iface).replace(":", "")

		raise FacterProcessorError("Could not find serial number or mac address")


	def find_device(self, data):
		device = None

		serialnum = data.get('serialnumber')
		if serialnum is not None:
			self.log.info("FindDev: by SerialNumber: %s", serialnum)
			device = self.session.query(Device).filter_by(instance_name=serialnum).first()

			if device:
				return device

		interfaces = data.get('interfaces')
		if interfaces is None:
			raise FacterProcessorError("Facter data does not provide interfaces list")

		for iface in interfaces.split(','):
			self.log.info("FindDev: by Interface: %s", iface)

			if not data.has_key("macaddress_%s" % iface):
				continue

			macname = data.get("macaddress_%s" % iface).replace(":", "")

			device = self.session.query(Device).filter_by(instance_name=macname).first()
			if device:
				return device

		return device


class_logger(FacterInfoProcessor)


class FacterImportCommand(MainCommand):

	NAME = 'fimport'
	USAGE = 'file'
	GROUP = 'data'
	OPTIONS = (
	 	Option('-n', '--no-submit', action='store_false', dest='submit', default=True),
    )

	def validate(self):
		if len(self.args) < 1:
			raise CommandArgumentError(self, "Must specify a file/dir to add")


	@with_session
	def execute(self, session):
		if self.cli:
			self.cli.increase_verbose()

		proc = FacterInfoProcessor(session)

		for path in self.arg_iterator():
			session.open_changeset()

			f = open(path)
			text = f.read()
			f.close()
			for data in yaml.load_all(text):
				proc.process(data)

		if self.option.submit:
			self.log.fine("Submitting Objects: %s / %s " % (len(session.new), len(session.dirty)))
			cs = session.submit_changeset()
			self.log.info("Committed Changeset: " + str(cs))

		else:
			session.revert_changeset()
			self.log.info("Not submitting")


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




