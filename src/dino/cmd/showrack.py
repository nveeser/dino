#/usr/bin/env python
import sys

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import (Rack, Device, ObjectSpec, ElementName, InvalidObjectSpecError)

class ShowRackCommand(MainCommand):
    NAME = "showrack"
    USAGE = " Rack/<RackId>"
    GROUP = "deprecated"
    
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "command must have one object argument")            
    
    @with_session
    def execute(self, session):        
        oname = ObjectSpec.parse(self.args[0], expected=ElementName)
        assert oname.entity_name == 'Rack', 'Object spec must have an EntityName of Rack'
            
        rack = session.find_element(oname)
        
        display_proc = rack.display_processor()
                
        string_list = list( display_proc.show(rack) )
        
        
        if not self.cli:
            return string_list
        
        for line in string_list:
            print line
            
