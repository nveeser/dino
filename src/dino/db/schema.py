#!/usr/bin/env python

import os
import sys
import re
from StringIO import StringIO

from sqlalchemy import func, types
from sqlalchemy import orm, engine
from sqlalchemy.schema import Table, Column, MetaData, ForeignKey
from sqlalchemy.orm import ColumnProperty, validates

import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany, OneToOne

from element import Element, ResourceElement
from exception import *
from changeset import using_changeset
from extension import name_depends, IndexedList
import collection
import model
from model import IpType
from display import RackDisplayProcessor, SubnetDisplayProcessor
# 
# Elixir / SQLAlchemy Metadata
#
# Prevent Elixir from using its own ScopedSessions
__session__ = None
__entity_collection__ = entity_set = collection.EntityCollection()
__metadata__ = metadata = MetaData()


SCHEMA_VERSION = 0x020110 # 020109 == 2.1.9

class SchemaInfo(elixir.Entity):    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='schema_info')
    elixir.using_table_options(mysql_engine='InnoDB') 
    using_changeset()

    #
    # Fields
    # 
    version = Field(types.Integer())
    protected = Field(types.Boolean())
    model_version = SCHEMA_VERSION
    
    #
    # Methods
    #
    def __init__(self):
        self.version = self.model_version
        self.protected = False
        
    def version_match(self):
        return self.version == self.model_version

    def assert_version_match(self):
        if self.version != self.model_version:
            raise SchemaVersionMismatch(self)
    
    def real(self):
        return self.id is not None
        
    @classmethod
    def find(cls, session, schema_name):
        stmt = '''SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = '%s' 
                    AND table_name = 'schema_info' 
                ''' % schema_name
            
        info = None
        if session.execute(stmt).scalar() > 0:
            info = session.query(cls).first()
            
        if info:
            session.expunge(info)
        else:
            info = cls() 
            
        return info
        
    @classmethod
    def create(cls, session):
        session.open_changeset()
        session.add(cls())
        session.submit_changeset()
        

# # # # # # # # # # # # # # # # # # # 
#  Inventory
# # # # # # # # # # # # # # # # # # # 

class Device(Element, model.Device):
    '''
    This is the main device Element
    '''
    INSTANCE_NAME_ATTRIBUTE = "hid"

    #
    # Metadata Options
    #    
    elixir.using_options(tablename='device')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
 
    #
    # Fields
    # 
    hid = Field( types.String(40), index=True )   
    hw_type = Field( types.String(32), default="unknown" )
    status = Field(types.String(32), default="inventory") # values: 'INVENTORY', 'ACTIVE','BROKEN','DEAD', 'RMA'
    notes = Field(types.Text, nullable=False, default="")   
    rackpos = Field(types.Integer, default=None) # range: 1-48
    serialno = Field(types.String(256), nullable=False)
    hw_class = Field(types.String(32), nullable=False, default="server") # values: 'server', 'router', 'switch', 'console', 'pdu'
    pdu_module = Field(types.String(16), default="0")
    pdu_port = Field(types.String(32), default="0")
    console_port = Field(types.String(16), default="")
    switch_port = Field(types.String(16), default="")

    #
    # Relationships
    #
    host = OneToOne('Host', cascade='all')    
    ports = OneToMany('Port', cascade='all, delete-orphan') #, collection_class=IndexedList.factory('name'))
    rack = ManyToOne('Rack', required=True, lazy=False)
    
    
    pdu = ManyToOne("Device")
    console = ManyToOne("Device")
    switch = ManyToOne("Device")

    chassis = ManyToOne('Chassis', required=True)
 
    @property
    def site(self):
        if self.rack:
            return self.rack.site
        else:
            return None



class Port(Element):
    #INSTANCE_NAME_ATTRIBUTE = "mac"
    #
    # Metadata Options
    #
    elixir.using_options(tablename='port')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
        
    #
    # Fields
    #
    
    name = Field(types.String(64), nullable=False)
    mac = Field(types.String(64), nullable=False, index=True)
    vlan = Field(types.Integer, nullable=False, default=0)
    is_blessed = Field(types.Boolean, nullable=False, default=False)
    is_ipmi = Field(types.Boolean, nullable=False, default=False)

    #
    # Relationships
    #
    device = ManyToOne('Device', required=True)
    #interface = OneToOne('Interface', cascade='all, delete-orphan')
    #link = ManyToOne('Link')
    #vlan = ManyToOne('Vlan')

    @property
    def interface(self):
        if self.device.host:       
            for iface in self.device.host.interfaces:
                if iface.port_name == self.name:
                    return iface          
        
        return None

    def derive_name(self):
        return "%s_%s" % (self.mac, self.name)

#
#class Link(Element):
#    #
#    # Metadata Options
#    #
#    elixir.using_options(tablename='link')
#    elixir.using_table_options(mysql_engine='InnoDB')
#    using_changeset()  
#
#    ports = OneToMany('Ports')
#
#    def derive_name(self):
#        if len(self.ports) == 2:
#            return "%s_%s" % (self.ports[0].instance_name, self.ports[1].instance_name)
#        else:
#            return None 



# # # # # # # # # # # # # # # # # # # 
#  Configuration
# # # # # # # # # # # # # # # # # # # 
    
        
class Host(Element):
    INSTANCE_NAME_ATTRIBUTE = "name"

    #
    # Metadata Options
    #    
    elixir.using_options(tablename='host')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()    

    #
    # Fields
    # 
    name = Field(types.String(128), index=True)
    
    #
    # Relationships
    #
    device = ManyToOne('Device', lazy=False)   
    interfaces = OneToMany('Interface', cascade='all, delete-orphan') #, collection_class=IndexedList.factory('port_name'))

    pod = ManyToOne('Pod', required=True, lazy=False)
    appliance = ManyToOne('Appliance')    
    ssh_key_info = OneToOne('SshKeyInfo', cascade='all, delete-orphan')
    
    @property
    def site(self):
        if self.device is not None:
            return self.device.site
        else:
            return None

    def hostname(self):
        return "%s.%s.%s" % (self.name, self.pod.name, self.site.name)

    @name_depends( 'Pod.name', 'Device;Rack;Site.name' )
    def derive_name(self):
        if self.pod is not None and self.site is not None:
            return "%s.%s.%s" % (self.name, self.pod.name, self.site.name)

    
    
class Interface(Element): 
    #
    # Metadata Options
    #
    elixir.using_options(tablename='interface')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    #
    # Fields
    #
    ifindex = Field(types.String(32), nullable=True)
    port_name = Field(types.String(64), nullable=False)
         
    #
    # Relationships
    #
    #port = ManyToOne('Port', required=True)
    host = ManyToOne('Host', required=True)
    address = OneToOne('IpAddress', cascade='all, delete-orphan')

    #
    # Methods
    #
    @name_depends( 'Host.instance_name' ) 
    def derive_name(self):
        if self.host is not None:
            if self.ifindex:                
                return "%s_%s_%s" % (self.host.derive_name(), self.port_name, self.ifindex)
            else:
                return "%s_%s" % (self.host.derive_name(), self.port_name)

#    @property
#    def host(self):
#        return self.port.device.host
    
    @property
    def port(self):
        if self.host.device:
            for port in self.host.device.ports:
                if port.name == self.port_name:
                    return port
                    
        return None        
        
    def name(self):
        if self.ifindex:
            return "%s:%s" % (self.port.name, self.ifindex)
        else:
            return self.port.name
        

class DnsRecord(Element):
    INSTANCE_NAME_ATTRIBUTE = "data"
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='dns_record')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
   
    #
    # Fields
    #      
    data = Field(types.String(255), index=True)      
    reverse = Field(types.Boolean, default=False)

    #
    # Relationships
    #
    address = ManyToOne("IpAddress", required=True) 



class SshKeyInfo(Element):
    #
    # Metadata Options
    #
    elixir.using_options(tablename='ssh_key_info')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
        
    #
    # Fields
    #      
    rsa_key = Field(types.Text)
    rsa_pub = Field(types.Text)
    dsa_key = Field(types.Text)
    dsa_pub = Field(types.Text)    

    #
    # Relationships
    #
    host = ManyToOne("Host", required=True)
    
    #
    # Methods
    # 
    @name_depends( 'Host.instance_name' ) 
    def derive_name(self):
        if self.host:
            return "KEYS-%s" % self.host.derive_name()
           
# # # # # # # # # # # # # # # # # # # 
#  Network 
# # # # # # # # # # # # # # # # # # # 


class IpAddress(Element, model.IpAddress, ResourceElement):
    INSTANCE_NAME_ATTRIBUTE = "value"
    #
    # Metadata Options
    #
    elixir.using_options(tablename='ip')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
 
    #
    # Fields
    #  
    value = Field(IpType(), index=True)    

    #
    # Relationships
    #      
    interface = ManyToOne('Interface', required=True)
    dnsrecords = OneToMany('DnsRecord', cascade='all', collection_class=set)
    subnet = ManyToOne('Subnet', ondelete="RESTRICT", onupdate="RESTRICT")

    def __init__(self, *args, **kwargs):
        self.__dict__['_subnet'] = None
        Element.__init__(self, *args, **kwargs)

    @classmethod
    def create_resource(cls, session, value, parent_iface):
        ''' <ipaddress>            
        '''
        assert isinstance(parent_iface, Interface), "Parent Object must be an Inteface"
        # Create IP
        ip = IpAddress(value=value)
        session.add(ip)
        
        # Check for existing IP
        existing_ip = session.find_element(ip.derive_element_name())        
        if existing_ip is not None:
            if parent_iface.address and parent_iface.address.value == ip.value:
                return existing_ip
            else:
                raise ResourceCreationError("Ip already assigned: %s (to %s)" % (value, existing_ip.interface))
 
        # Check if IP exists on Range
        subnet = ip.query_subnet()
        if subnet is None:
            raise ResourceCreationError("No Subnet found to assign IP to: %s" % ip)

        for range in subnet.ranges:
            if range.contains(ip):
                raise ResourceCreationError("Ip exists on Subnet Range: %s" % range)
        
        return ip
    
        
class Subnet(Element, model.Subnet):
    DISPLAY_PROCESSOR = SubnetDisplayProcessor

    #
    # Metadata Options
    #    
    elixir.using_options(tablename='subnet')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()

    #
    # Fields
    #     
    addr = Field(IpType(), index=True, nullable=False)
    mask_len = Field(types.Integer, nullable=False, default="24")
    gateway = Field(types.Integer, nullable=False, default="1")
    
    description = Field(types.String(256), nullable=False, default="")
    is_assigned = Field(types.Boolean, nullable=False, default=True)
    is_active = Field(types.Boolean, nullable=False, default=True)
    is_console = Field(types.Boolean, nullable=False, default=False)

    #
    # Relationships
    #    
    parent = ManyToOne('Subnet')
    children = OneToMany('Subnet', inverse='parent')
    site = ManyToOne('Site')
    admin_info = OneToOne('SubnetAdminInfo', cascade='all, delete-orphan')
    ranges = OneToMany('Range', cascade='all, delete-orphan', collection_class=list)
    addresses = OneToMany('IpAddress', collection_class=set)
    
    #owner_device = ManyToOne('Device')
    #vlan = ManyToOne('Vlan', required=True)
    
    #
    # Methods
    #    
    def __init__(self, **kwargs): 
        if 'addr' not in kwargs:
            return
              
        if 'mask_len' not in kwargs:        
            parts = kwargs['addr'].split("/")
            if len(parts) != 2:
                raise ValueError("Must specify length for the subnet")
                
            kwargs['addr'] = parts[0]
            kwargs['mask_len'] = int(parts[1])
            
        self.set(**kwargs)                
        self.naddr = (self.naddr & self.nmask) & 0xFFFFFFFF
        
    def derive_name(self):
        if self.addr is not None and self.mask_len is not None:
            return "%s_%d" % (self.addr, self.mask_len) 
    
        
    

class SubnetAdminInfo(Element):

    #
    # Metadata Options
    #
    elixir.using_options(tablename='subnet_admin_info')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()

    #
    # Fields
    #     
    description = Field(types.String(256), nullable=False, default="")
    acquired_time = Field(types.Integer, default=0)
    
    #
    # Relationships
    #
    subnet = ManyToOne('Subnet')
    
    #
    # Methods
    #
    @name_depends( 'Subnet.instance_name' )
    def derive_name(self):
        if self.subnet is not None:
            return "INFO-%s" % (self.subnet.derive_name()) 
                  

class Range(Element, model.Range, ResourceElement):
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='range', inheritance='single')
    elixir.using_table_options(mysql_engine='InnoDB')       
    using_changeset()

    #
    # Fields
    #     
    start = Field( types.Integer(), nullable=False)
    end = Field( types.Integer(), nullable=False )
    range_type = Field( types.String(20), nullable=False )
    description = Field(types.String(256) )

    #
    # Relationships
    #
    subnet = ManyToOne("Subnet")


           
    #
    # Methods
    #
    @classmethod
    def create_empty(cls):
        return cls(None, None, None, None)
    
    @name_depends( 'Subnet.instance_name' )
    def derive_name(self):
        if self.subnet is not None:
            return "%s-%s-%s" % (self.subnet.derive_name(), self.start, self.end) 
    
    def __init__(self, subnet=None, start=None, end=None, range_type=None, **kwargs):
        kwargs['subnet'] = subnet
        kwargs['start'] = start
        kwargs['end'] = end
        kwargs['range_type'] = range_type
        
        self.set(**kwargs)
    
    @classmethod
    def create_resource(cls, session, value, parent_subnet):
        '''<range_type>(<start>-<end>)
        range_type := { dhcp | policy }
        start := integer offset 
        end := integer offset
        (offset from first network address of the subnet)
        '''
        assert isinstance(parent_subnet, Subnet)
    
        m = re.match("(\w+)\((\d+)-(\d+)\)", value)
        if m is None:
            raise ResourceCreationError("Resource String does not match format: <range_type>(<start>-<end>): %s" % value)
            
        (range_type, start, end) = m.groups()
        return Range(range_type=range_type, start=int(start), end=int(end), subnet=parent_subnet)
        
#class Vlan(Element, model.Range):    
#    INSTANCE_NAME_ATTRIBUTE = 'name'
#    
#    #
#    # Metadata Options
#    #
#    elixir.using_options(tablename='vlan')
#    elixir.using_table_options(mysql_engine='InnoDB')       
#    using_changeset()
#
#    #
#    # Fields
#    # 
#    name = Field(types.String(32))    
#    ports = OneToMany('Port')
#    subnet = OneToOne('Subnet')
    

# # # # # # # # # # # # # # # # # # # 
#  Property Set  
# # # # # # # # # # # # # # # # # # # 

class PropertySet(elixir.Entity):

    #
    # Metadata Options
    #
    elixir.using_options(tablename='property_set')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    #
    # Fields
    # 
    name = Field(types.String(32))
    value = Field(types.String(32))
    description = Field(types.String(255))
    
    #
    # Relationships
    #
    properties = OneToMany("Property", cascade='all, delete-orphan')

        
class Property(elixir.Entity):
    #
    # Metadata Options
    #    
    elixir.using_options(tablename='property')
    elixir.using_table_options(mysql_engine='InnoDB')

    #
    # Fields
    #     
    name = Field(types.String(32))
    value = Field(types.String(32))
    description = Field(types.String(255))
    
    #
    # Relationships
    #
    property_set = ManyToOne('PropertySet', required=True)

       
       
       

# # # # # # # # # # # # # # # # # # # 
#  Lookup Tables (better name)
# # # # # # # # # # # # # # # # # # # 
            
class Site(Element):
    INSTANCE_NAME_ATTRIBUTE = "name"
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='site')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    #
    # Fields
    # 
    name = Field( types.String(32), nullable=False, index=True)    
    is_active = Field( types.Boolean, nullable=False, default=True)
    address1 = Field( types.String(80), nullable=False)
    address2 = Field( types.String(80), nullable=False, default="")
    city = Field( types.String(64), nullable=False)
    state = Field( types.String(2), nullable=False)
    postal = Field( types.String(16), nullable=False)
    description = Field( types.String(255) )
    ownership = Field( types.String(16), default='production')   # values: 'ops', 'dev', 'production', 'other'
    sitetype = Field( types.String(10), default='cage') # values: 'cage', 'colo', 'man', 'office', 'closet'
    timezone = Field( types.String(20), default='-7') 


class Rack(Element):    
    INSTANCE_NAME_ATTRIBUTE = "name"
    DISPLAY_PROCESSOR = RackDisplayProcessor
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='rack')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    #
    # Fields
    #    
    name = Field(types.String(128), index=True)
    location = Field(types.String(32), default="inventory")
    size = Field(types.Integer(), default=48)
    
    #
    # Relationships
    #
    devices = OneToMany('Device')    
    site = ManyToOne('Site', required=True, lazy=False)

    #
    # Methods
    # 
    @name_depends( 'Site.instance_name' )   
    def derive_name(self):
        if self.site is not None:
            return "%s.%s" % (self.site.derive_name(), self.name)

class Pod(Element):
    ''' Logical Grouping of Hosts '''
    INSTANCE_NAME_ATTRIBUTE = "name"
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='pod')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    #
    # Fields
    # 
    name = Field(types.String(64), nullable=False, index=True)
    description = Field(types.String(128), nullable=False, default="")

 
 
class OperatingSystem(Element):
    INSTANCE_NAME_ATTRIBUTE = "name"
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='os')
    elixir.using_table_options(mysql_engine='InnoDB')

    #
    # Fields
    # 
    name = Field(types.String(128), nullable=False)   
    applicances = OneToMany('Appliance', cascade='all')


class Appliance(Element):    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='appliance')
    elixir.using_table_options(mysql_engine='InnoDB')

    #
    # Fields
    #     
    name = Field(types.String(128), nullable=False)
    
    #
    # Relationships
    #
    os = ManyToOne('OperatingSystem', lazy=False)

    #
    # Methods
    #    
    @name_depends( 'OperatingSystem.instance_name' )
    def derive_name(self):
        if self.os is not None:
            return "%s(%s)" % (self.name, self.os.derive_name())
        


class Chassis(Element):
    INSTANCE_NAME_ATTRIBUTE = "name"
    
    #
    # Metadata Options
    #
    elixir.using_options(tablename='chassis')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    #
    # Fields
    #     
    name = Field(types.String(128), nullable=False)
    vendor = Field(types.String(128), nullable=False)
    product = Field(types.String(128), nullable=False)
    racksize = Field(types.Integer, nullable=False, default=2) # values: 0-48
    description = Field(types.String(255), nullable=False, default="")



elixir.setup_entities(__entity_collection__)  




