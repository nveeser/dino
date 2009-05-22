import sys

from dino.cmd.command import AbstractCommandInterface, CommandMeta, with_session, with_connection
from dino.cmd.maincmd import MainCommand, ClassSubCommand
from dino.cmd.exception import *

from dino.db import Subnet, IpType, IpAddress, ObjectSpec, ElementName, ResourceCreationError

    
class IpCommand(ClassSubCommand):
    '''Commands to deal with ip addresses, etc '''
            
    NAME = 'ip'
    USAGE = '<subcommand>'
    GROUP = "query"


class IpSubCommand(AbstractCommandInterface):
    '''Base of all ip subcommands'''
    NAME = None
    
    __metaclass__ = CommandMeta

    def __init__(self, db_config, cli=None):
        self.db_config = db_config
        self.cli=cli
    
    def execute(self):
        raise NotImplemented()

    def parse(self, args):
        (self.option, self.args) = self.parser.parse_args(args=args)

    def print_usage(self):
        print self.prog_name + " " + self.MAIN_COMMAND_NAME + " " + self.NAME + " " + self.USAGE
    
    def print_help(self):
        print "   ", self.__class__.__doc__

ClassSubCommand.set_subcommand(IpCommand, IpSubCommand) 
    

class AvailCommand(IpSubCommand):
    ''' Print next available IP on Subnet 
    If specified, <count> addresses are returned '''
    
    #Find all leafs in the parent tree
    #SELECT a.* FROM subnet AS a 
    #    LEFT OUTER JOIN subnet as b ON (b.parent_id = a.id)
    #    WHERE where b.id IS NULL
    #q = session.query(Subnet)\
    #    .filter(Subnet.addr == subnet_name)\
    #    .outerjoin('parent', aliased=True)\
    #   .filter(Subnet.id == None)

        
    NAME = 'avail'    
    USAGE = 'Subnet/<InstanceName> [ <count> ]'
    
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specifiy a Subnet")
        
        self.oname = ObjectSpec.parse(self.args[0], expected=ElementName)
        
        if len(self.args) == 2:
            self.count = int(self.args[1])
        else:
            self.count = 1
                
    @with_session
    def execute(self, session):
        #Find the subnet of this name with the longest netmask
        # SELECT subnet.*  FROM subnet 
        #    WHERE subnet.addr = :addr_1 ORDER BY subnet.mask_len DESC
        
        subnet = session.find_element(self.oname)
        
        if not subnet:
            raise CommandExecutionError(self, "Subnet not found: %s" % subnet_name)
            sys.exit(1)
        
        self.log.fine("Found: %s", subnet)
        
        ip_list = list(subnet.avail_ip_set())
        ip_list.sort()
        ip_list = map(IpType.ntoa, ip_list)
                        
        if len(ip_list) < self.count:
            raise CommandExecutionError(self, "Requested count of addresses not available: %s" % self.count)

        if len(ip_list) > self.count:    
            ip_list = ip_list[0:self.count]
            
        if self.cli is None:
            return ip_list
        
        for x in ip_list:
            print x
            
            
class SetIpCommand(IpSubCommand):
    '''Commands to deal with ip addresses, etc '''
            
    NAME = 'set'
    USAGE = 'Interface/<InstanceName> <IpAddress>'
    GROUP = "query"
    
    
    def validate(self):
        if len(self.args) != 2:
            raise CommandArgumentError(self, "Must supply in Interface and Address")
        
    @with_session
    def execute(self, session):
        (interface_name, ip_value) = self.args
        
        oname = ObjectSpec.parse(interface_name, expected=ElementName)
        
        if oname.entity_name != "Interface":
            raise CommandArgumentError(self, "Element must be of type Interface.  Supplied: %s" % oname.entity_name)

        iface = session.resolve_element_spec(oname)
        
        if iface.address is not None and iface.address.value == ip_value:
            self.log.info("Ip is already set")
            return
        
        try:            
            session.open_changeset()
            iface.address = IpAddress.create_resource(session, ip_value, iface)            
            cs = session.submit_changeset()
            
        except ResourceCreationError, e:
            raise CommandExecutionError(self, str(e))
                        
        
        self.log.info("Submitted: %s", cs)
        
        
        
        