import logging
try:
    import json
except ImportError:
    import simplejson as json

import sqlalchemy
from sqlalchemy import and_

from dino.cmd.exception import *
from dino.cmd.ip import IpCommand
from dino.db.schema import * 
from dino.db.objectspec import *

import pprint; pp = pprint.PrettyPrinter(indent=4)


'''
Basic tenets of the json importer: 
----------------------------------

1) A json file is a complete description for a single device. 

2) A device is comprised of many elements, each with a unique instance_name 
   and entity_name.  Elements are represented as objects in dino's ORM.

3) Instances of an element can be expressed as a string like so: 
   "Element:instance_name", where Element is a class of object, and 
   instance_name is a unique string describing an instance of that element.   

     Examples:   
         "Device:a5s1.net"
         "Host:app04.p01.sjc1"
         "Interface:app04.p01.sjc1_eth0"
         "IpAddress:172.29.5.24"

4) Elements in the ORM can have many relationships with other elements, 
   but certain elements cannot exist in dino without an owner element.

     Examples: 
     * A Device element is the owner of Host elements and Port elements
     * A Host element is the owner of Interface elements
     * An Interface element is the owner of IpAddress elements

5) Device elements have no owner, because they are the root of the 
   element tree.  Each Device can be seen as a container for various 
   combinations of Physical hardware elements (such as Ports), and 
   configuration elements such as Hosts, Interfaces, IpAddresses, etc.
''' 


class JsonProcessor(object):    

    '''
    Process the old json format into a new nested struct (v2 format).
    Then insert all records, using a precise ordering to eliminate 
    problems with parentage.
    ''' 

    log = logging.getLogger("dino.cmd.json.processor")

    def __init__(self, cmd, session):
        self.cmd = cmd
        self.session = session


    def host_to_json(self, host):  

        hname = str(host.instance_name).split('.')

        # some initial structs
        E = ['Device:', 'Host:', 'Port:', 'Interface:', 'IpAddress:'] 
        data = {}
        # add v2 header.
        data['Header'] = { "version" : 2, "type": "server" }

        # host 
        h = str(host.element_name)
        data[h] = {}
        data[h]['id'] = host.id
        data[h]['name'] = hname[0]
        data[h]['pod'] = str(host.pod)
        data[h]['device'] = str(host.device)
        data[h]['appliance'] = str(host.appliance)

        # device
        device = host.device
        d = data[h]['device']
        data[d] = {}
        data[d]['hid'] = device.hid
        data[d]['hw_type'] = device.hw_type
        data[d]['status'] = device.status
        data[d]['notes'] = device.notes
        data[d]['rackpos'] = device.rackpos
        data[d]['serialno'] = device.serialno
        data[d]['pdu_port'] = device.pdu_port
        data[d]['hw_class'] = device.hw_class
        if data[d]['hw_class'] != 'server':
            data['Header']['type'] = 'special'
        data[d]['rack'] = str(device.rack)
        data[d]['console'] = str(device.console)
        data[d]['switch'] = str(device.switch)
        data[d]['chassis'] = str(device.chassis)

        # ports
        ports = device.ports
        for port in ports:
            p = str(port)
            data[p] = {}
            data[p]['name'] = port.name
            data[p]['mac'] = port.mac
            data[p]['vlan'] = port.vlan
            data[p]['is_blessed'] = port.is_blessed
            data[p]['is_ipmi'] = port.is_ipmi
            data[p]['device'] = str(port.device)
            interface = port.interface
            if interface: 
                i = str(interface)
                data[i] = {}
                data[i]['port'] = str(interface.port)
                address = interface.address
                if address: 
                    ip = str(address)
                    data[ip] = {}
                    data[ip]['interface'] = str(address.interface)
                    data[ip]['subnet'] = str(address.subnet)
                    (a, b) = str(address).split(':')
                    data[ip]['value'] = b
        
        #data = verify(self.session, data)    
        return json.dumps(data, indent=4)
    

    def process(self, filepath):  

        elements = ['Device:', 'Host:', 'Port:', 'Interface:', 'IpAddress:'] 
        self.log.info("Read file: %s", filepath)
        data = json.load(open(filepath)) 
        # asserts new format, then verifies.
            
        # if no header, assume v1 format.
        
        if not data.has_key('Header'): 
            data = self.v1_transform(data)
            
        data = self.verify(data)    
    
        #pp.pprint(data)

        self.instances = {}
        
        for spec in data.keys():
            instance = is_known(self.session, spec)
            
            if instance is None:
                self.log.info("  Adding new %s" % spec) 
                oname = ObjectSpec.parse(spec, expected=ElementName)
                instance = self.session.resolve_entity(oname.entity_name).create_empty()
                self.session.add(instance)
            else:
                self.log.info("  Updating %s" % spec)

            self.instances[spec] = instance

        
        
        for spec in data.keys():
            instance = self.instances[spec]            
            for key, value in data[spec].items():
                if data.has_key(value):
                    value = self.instances[value]
                                        
                setattr(instance, key, value)
            
            #print spec, instance.instance_name
        return 
        
    
    
    def verify(self, data):
        '''
        Look in v2 header for clues about what operation we're performing, 
        e.g. a full server insertion, a special device insertion, etc.
        Run the appropriate verification for that context.
        '''
    
        if data.has_key('Header') and data['Header'].has_key('type'):
    
            if data['Header']['type'] == 'server':
                self._verify_server(data)
            elif data['Header']['type'] == 'special':
                self._verify_special(data)
            else: 
                err = 'Passed in Header that has no update type.\n'
                CommandExecutionError(self.cmd, err)
            
            data.pop('Header')
            
        else:
            err = 'Passed in json struct has no v2 header.\n'
            CommandExecutionError(self.cmd, err)
    
        return data
                
    
    
    def _verify_special(self, data):
    
        '''
        Verify the special device data we're about to import. Special 
        devices include routers, switches, devices, and PDUs. Routers
        and switches often have no port or interface info, so the 
        verification process is different from a server.. 
        '''
        
        count = { 'device':    0, 
                  'host':      0, 
                  'port':      0, 
                  'interface': 0, 
                  'addr':      0 }
    
        critical = False
    
        # clear null keys
        for e, edict in data.items():
            for key, val in edict.items():
                if not val or val == "None":
                    edict.pop(key)
    
        for e, edict in data.items():
    
            if e.startswith('Device:'):
                count['device'] += 1
        
                # Rack must be known.
                rack = is_known(self.session, edict['rack'])
                if not rack: 
                    critical = True 
                    self.log.warn('Rack: %s does not exist.\n' % edict['rack'])
                data[e]['rack'] = rack
    
                # Chassis must be known.
                chassis = is_known(self.session, edict['chassis'])
                if not chassis: 
                    critical = True 
                    self.log.warn('Chassis: %s does not exist.\n'
                                  % edict['chassis'])
                data[e]['chassis'] = chassis
    
            if e.startswith('Host:'):
                count['host'] += 1
    
                # Pod must be known.
                pod = is_known(self.session, edict['pod'])
                if not pod: 
                    critical = True 
                    self.log.warn('Pod: %s does not exist.\n' % edict['pod'])
                data[e]['pod'] = pod
    
    
            # unnamed ethernet ports are lo0, by convention.
            # (ports on consoles and PDUs are unnamed.)
            if e.startswith('Port:'):
                count['port'] += 1
                if not data[e]['name'] == 'lo0':
                    critical = True
                    self.log.warn('Port: %s should be named lo0' 
                                  % edict['name'])
    
            if e.startswith('Interface:'):
                count['interface'] += 1
    
            if e.startswith('IpAddress:'):
                subnet = is_known(self.session, edict['subnet'])
                if not subnet: 
                    critical = True 
                    self.log.warn('Subnet: %s does not exist.\n'
                                   % edict['subnet'])
                data[e]['subnet'] = subnet
                count['addr'] += 1
    
    
        # sanity check element counts
        if not count['device'] == 1: 
            critical = True
            self.log.warn('Data should contain 1 device, not %s.\n' 
                          % count['device'])
        if not count['host'] == 1:
            critical = True
            self.log.warn('Data should contain 1 host, not %s.\n' 
                          % count['host'])
        #if not count['interface'] == 1:
        #    critical = True
        #    self.log.warn('Data should contain 1 interface, not %s.\n' 
        #                  % (count['interface']))
        #if not count['addr'] == count['interface']:
        #    self.log.warn('Data should have 1 address per interface. \
        #                   Ifaces: %s, Addrs: %s\n'
        #                  % (count['interface'], count['addr']))
        #    critical = True
       
        # stop if there are critical errors.
        if critical: 
            err = '''Critical errors were found in the validation process
                    for special device: %s. Please see log for details.\n'''
            raise CommandExecutionError(self.cmd, (err % 'special'))
    
        return(data)
       
        
           
    def _verify_server(self, data):
    
    
        '''
        Verify the server data we're about to import.  Prepare it for 
        the ORM import process.  If critical errors are found, populate 
        an abort function with messages.
    
        NOTE: when an object in the cache is checked for its existence in 
              dino, we then cache the object at the point where the instance
              name used to be. This expedites the import process later on.
        '''
    
        count = { 'device':    0, 
                  'host':      0, 
                  'port':      0, 
                  'interface': 0, 
                  'addr':      0, 
                  'console':   0, 
                  'ipmi':      0, 
                  'bport':     0 }
    
        critical = False
    
        # clear null keys
#        for e, edict in data.items():
#            for key, val in edict.items():
#                if not val or val == "None":
#                    edict.pop(key)
    
        for e, edict in data.items():
    
            if e.startswith('Device:'):
                count['device'] += 1
    
                # Rack must be known.
                rack = is_known(self.session, edict['rack'])
                if not rack: 
                    critical = True 
                    self.log.warn('Rack: %s does not exist.\n' % edict['rack'])
                data[e]['rack'] = rack
    
                # Chassis must be known.
                chassis = is_known(self.session, edict['chassis'])
                if not chassis: 
                    critical = True 
                    self.log.warn('Chassis: %s does not exist.\n'
                                   % edict['chassis'])
                data[e]['chassis'] = chassis
    
                # Console must be known, if given.
                if edict.has_key('console') and edict['console'].startswith('Device:'):
                    # must be an instance name
                    console = is_known(self.session, edict['console'])
                    if not console:
                        critical = True 
                        (a, b) = edict['console'].split(':')
                        self.log.warn('Console: %s does not exist.\n' % b)
                    else: 
                        data[e]['console'] = console
    
                # Switch must be known
                data[e]['switch'] = None
                if edict['switch']:
                    switch = is_known(self.session, edict['switch'])
                    if not switch:
                        critical = True
                        self.log.warn('Switch: %s does not exist.\n' % edict['switch'])
                    else:
                        data[e]['switch'] = switch
                        
                
    
            if e.startswith('Host:'):
                count['host'] += 1
    
                # Pod must be known.
                pod = is_known(self.session, edict['pod'])
                if not pod: 
                    critical = True 
                    self.log.warn('Pod: %s does not exist.\n' % edict['pod'])
                data[e]['pod'] = pod
    
                # Appliance must be known
                appliance = is_known(self.session, edict['appliance'])
                if not appliance: 
                    critical = True 
                    self.log.warn('Appliance: %s does not exist.\n' 
                                  % edict['appliance'])
                data[e]['appliance'] = appliance 
       
            if e.startswith('Port:'):
                count['port'] += 1
                # check blessed flag
                if edict.has_key('is_blessed') and edict['is_blessed'] == 1:
                    count['bport'] += 1
    
                # ipmi flag is properly set
                if edict['name'] is 'ipmi':
                    edict['is_ipmi'] = 1
          
            if e.startswith('Interface:'):
                count['interface'] += 1
    
            if e.startswith('IpAddress:'):
                subnet = is_known(self.session, edict['subnet'])
                if not subnet: 
                    critical = True 
                    self.log.warn('Subnet: %s does not exist.\n'
                                   % edict['subnet'])
                data[e]['subnet'] = subnet
                count['addr'] += 1
    
    
        # sanity check element counts
        if not count['device'] == 1: 
            critical = True
            self.log.warn('Data should contain 1 device, not %s.\n' 
                          % count['device'])
        if not count['host'] == 1:
            critical = True
            self.log.warn('Data should contain 1 host, not %s.\n' 
                          % count['host'])
        if not count['port'] >= 1:
            critical = True
            self.log.warn('Data must contain at least 1 port.\n' 
                          % count['port'])
        if not count['interface'] <= count['port']:
            critical = True
            self.log.warn('Data contains %s interfaces, but only %s ports.\n' 
                          % (count['interface'], count['port']))
        if not count['addr'] == count['interface']:
            self.log.warn('Data should have 1 address per interface. \
                          Ifaces: %s, Addrs: %s\n'
                          % (count['interface'], count['addr']))
            critical = True
        if not count['bport'] == 1:
            critical = True
            self.log.warn('Data should contain 1 blessed port, not %s.\n' 
                          % count['bport'])
    
        # ipmi port should not be blessed port
        for e, edict in data.items():
            if e.startswith('Port:') and \
               edict.has_key('is_blessed') and edict['is_blessed'] == 1 and \
               edict.has_key('is_ipmi')    and edict['is_ipmi']    == 1:
                critical = True
                self.log.warn('ipmi port cannot be blessed port\n') 
    
        # must have either a console port, or an ipmi port.
        for e, edict in data.items():
            if e.startswith('Device:') and edict.has_key('console'): 
                count['console'] += 1
            if e.startswith('Port:') and edict.has_key('is_ipmi'):
                count['ipmi'] += 1
    
        if count['ipmi'] == 0 and count['console'] == 0:
            critical = 1
            self.log.warn('Must have either console or ipmi port.\n')
            
        # stop if there are critical errors.
        if critical: 
            err = '''Critical errors were found in the validation process. 
                            Please see the log for details.\n'''
            raise CommandExecutionError(self.cmd, err)
    
        return(data)
            
            



    def v1_transform(self, data_v1):
       
        '''
        Transform a dino 1.0 json description into a dino 2.0 json description.
        '''
       
        # initialize v2 struct
        data_v2 = {}
    
        # strip blank keys
        for key, val in data_v1.items():
            if val == 'None':
                data_v1.pop(key)
    
        # create object_specs for all elements. Each will become a key 
        # for its own dict.
    
        # some preliminaries
        E = ['Device', 'Host', 'Port', 'Interface', 'IpAddress']    
        bport = data_v1['blessed_port']
        if bport == "":
            raise RuntimeError("No Blessed port specified: ")
        bport_mac = data_v1['mac_port.mac ' + bport]
        hid = bport_mac.replace(":", "")
        hid = hid.upper()
    
        #
        # Device keys
        #
        Device = E[0] + ':' + hid
        data_v2[Device] = {}
        data_v2[Device]['hid']      =  hid
        data_v2[Device]['rackpos'] = data_v1.get('hnode.loc_rackpos', None)
        data_v2[Device]['serialno'] = data_v1.get('hnode.serialno', None)            
        data_v2[Device]['status']   =  data_v1.get('hnode.status', None)
        data_v2[Device]['hw_type']  =  data_v1.get('hnode.type_dict', None)
        if data_v2[Device]['hw_type'] == 'vm':  
            data_v2[Device]['hw_class'] = 'vm'
        else:
            data_v2[Device]['hw_class'] = 'server'
              
        data_v2[Device]['pdu_port'] =  data_v1.get('hnode.pdu_port', None)
   
        # related objects (stored as object specs)
    
        # rack
        if  data_v1.has_key('hnode.loc_row') and data_v1.has_key('hnode.loc_rack'):
            rack_spec = 'Rack:' + '.'.join([data_v1['site.domain'], 
                                            data_v1['hnode.loc_rack']])
        else:
            rack_spec = "Rack:%s.unknown" % data_v1['site.domain']
            
        data_v2[Device]['rack'] = rack_spec
    
        # chassis
        chassis_spec = 'Chassis:' + data_v1['model.name']
        data_v2[Device]['chassis'] = chassis_spec
    
        # console
        if data_v1.has_key('hnode.console_id'):
            tmp = data_v1['hnode.console_id'].split('.')
            console_host_spec = E[1] + ':' + '.'.join(tmp[:3])
            console_host = is_known(self.session, console_host_spec)
            if console_host is None: 
                self.log.info("  Cannot find console host: %s" % console_host_spec)
                data_v2[Device]['console'] = None
            else:
                data_v2[Device]['console'] = console_host.device.element_name
    
        # switch
        tmp = data_v1['switch_handle'].split('.')
        switch_host_spec = E[1] + ':' + '.'.join(tmp[:3])
        switch_host = is_known(self.session, switch_host_spec)
        if switch_host is None:
            self.log.info("  Cannot find switch host: %s" % switch_host_spec)
            data_v2[Device]['switch'] = None
        else:
            switch_device = switch_host.device
            data_v2[Device]['switch'] = switch_device.element_name
    
        #
        # host keys
        #
        handle = data_v1.get('hnode.handle', None)
        if handle is None:
            raise CommandExceptionError(self.cmd, "Could not find an hnode handle" ) 

        h = handle.split('.')
        short_name = '.'.join(h[:3])
        Host = E[1] + ':' + short_name
        data_v2[Host] = {}
        data_v2[Host]['name'] = h[0]
        data_v2[Host]['device'] = Device
        if data_v1.has_key('hnode.mw_tag') and data_v1['hnode.mw_tag'] != "":
            data_v2[Host]['id'] = int(data_v1['hnode.mw_tag']) 
    
        # pod
        pod_spec = 'Pod:' + h[1]
        data_v2[Host]['pod'] = pod_spec
    
        # appliance
        appliance_spec = 'Appliance:' + data_v1['appliance.name'] + \
                         '[' + data_v1['hnode.os_id'] + ']'
        data_v2[Host]['appliance'] = appliance_spec
    
        #
        # Ports
        #
        for key, val in data_v1.items():
            if key.startswith('mac_port.mac'):
                (x, iface) = key.split()
                mac = val.upper()
                Port = E[2] + ':' + mac + '_' + iface
                data_v2[Port] = {}
                data_v2[Port]['mac'] = mac
                data_v2[Port]['name'] = iface
                data_v2[Port]['device'] = Device
                # port flags
                if iface == 'ipmi':
                    data_v2[Port]['is_ipmi'] = 1
                else:
                    data_v2[Port]['is_ipmi'] = 0
                    
                if iface == bport:
                    data_v2[Port]['is_blessed'] = 1
                    data_v2[Port]['vlan'] = data_v1.get('mac_port.vlan', 0)
                else:
                    data_v2[Port]['is_blessed'] = 0
                    data_v2[Port]['vlan'] = 0
    
                #
                # Interfaces
                #
    
                # add only if there's a corresponding IP.
                if data_v1.has_key('ip_mac.addr ' + iface):
                    Interface = E[3] + ':' + '.'.join(h[:3]) + '_' + iface
                    data_v2[Interface] = {}
                    data_v2[Interface]['port_name'] = iface
                    data_v2[Interface]['host'] = Host
    
                #
                # IpAddresses
                #
                if data_v1.has_key('ip_mac.addr ' + iface):
                    ip = data_v1['ip_mac.addr ' + iface]
                    # if ip is from a range, reserve a new one. 
                    if is_dynamic(self.session, ip):
                        new_addr = get_ip(ip, iface)
                        ip = new_addr.instance_name
                    IpAddress = E[4] + ':' + ip
                    data_v2[IpAddress] = {}
                    # find my subnet
                    subnet = find_subnet(self.session, ip)
                    if subnet: 
                        data_v2[IpAddress]['subnet'] = 'Subnet:' + subnet.instance_name
                    data_v2[IpAddress]['interface'] = Interface
                    data_v2[IpAddress]['value'] = ip
    
        # NOTE: no dns names are added.
    
        # add v2 header.
        data_v2['Header'] = { "version" : 2, "type": "server" }
    
        return data_v2
    
      
def get_ip(addr, iface):    
    '''
    Get an IP.  Tries to return the IP passed-in, 
    but will retrun a valid IP in any case, one 
    that is guaranteed not to be part of any reserved
    range, and not already owned.
    '''

    if not addr or not iface:
        raise CommandExecutionError(self.cmd, "Bad params to _get_ip: %s / %s" % (addr, iface))
        
    reserver = IpCommand(self.db)
    iplist = reserver.sub_avail(addr)
    if len(iplist) < 1:
        raise CommandExecutionError(self.cmd, "No IP delivered by IP reserver!")
        # Free IP. 
        # Guaranteed not to be in a range, or already in use.
        addr = ip_list[0]

    ip = IpAddress(value=addr)

    return ip
   

def is_dynamic(session, addr):

    '''Discover if a passed-in IP falls within 
       any known dynamic dhcp range.'''

    sql = '''
          select 
              inet_ntoa(subnet.addr) as net, 
              subnet.mask_len as mask 
          from range, subnet 
          where 
              subnet_id = subnet.id and
              range.range_type = 'dhcp' and
              inet_aton('%s') 
                  between (subnet.addr + range.start) 
                  and (subnet.addr + range.end) 
          order by mask desc limit 1;
          ''' % addr 

    res = session.execute(sql)
    res = res.fetchone()
    if res:
        return True
    else:
        return False


def is_known(session, instance_name):

    '''Discover if a given element instance
       is known by dino. Does not include history.'''

#    if spec.entity_name == 'Device': 
#        # discover devices in a special way
#        instance = find_device(session, spec)
#    else: 
    
    instance = session.find_element(instance_name)

    if instance: 
        return instance
    else:
        return None


def find_device(session, spec):

    '''
    Looks through the possibile names for a device. If one 
    exists, it returns it. Otherwise it returns None.
    '''

    device = session.find_element(spec)
    if not device: 
        return None

    # get potential device names
    ports = device.ports
    names = [ p.mac.replace(':', '') for p in ports if not p.is_ipmi ]

    # found a viable name
    for name in names:
        if is_known(session, name):
            return name
    
    # found no name
    return None

   
def find_subnet(session, ip):

    '''
    Returns the subnet object for any passed-in IP 
    (in dotted quad form). Returns None if no subnet 
    matches.
    '''

    naddr = IpType.aton(ip)
    sql_netmask = func.power(2,32) - func.power(2, (32-Subnet.mask_len))

    q = session.query(Subnet).filter(
        Subnet.addr == sql_netmask.op('&')(naddr)
        ).order_by( Subnet.mask_len.desc() )

    return q.first()



