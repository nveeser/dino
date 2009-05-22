
import elixir

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.help import HelpCommand
from dino.cmd.exception import *

from dino.db import ObjectSpec


class ListCommand(MainCommand):
    ''' List all the instances in the database for a given element'''
    NAME = "list"
    USAGE = "<EntityName>"
    GROUP = "deprecated"
    
    @classmethod
    def print_usage(cls):
        print cls.NAME + " " + cls.USAGE

    def print_help(cls):
        HelpCommand.list_elements()        

    def validate(self):
        if len(self.args) != 1:
            raise CommandArgumentError(self, "list command must have one object argument")

    @with_session
    def execute(self, session):
        entity_name = self.args[0]
        
        if ObjectSpec.SEPARATOR in entity_name:
            raise CommandArgumentError(self, "This looks like an ElementName, not a EntityName: %s" % entity_name)

        try:            
            entity = self.db_config.resolve(entity_name)            
            for r in session.query(entity).all():
                print r
                
        except KeyError, e:
            print "ERROR: Unknown Entity: ", entity_name
            self.usage()
        
        
