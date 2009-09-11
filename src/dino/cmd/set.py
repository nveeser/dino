from optparse import Option

import sqlalchemy.orm.properties as sa_props

from dino.config import class_logger
from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import *

class SetCommand(MainCommand):
    NAME = "set"
    USAGE = "<ElementName>/<PropertyName> <Value>"
    GROUP = "element"
    OPTIONS = ( 
        Option('-n', '--no-commit',  dest='no_commit', action='store_true', default=False), 
    )
    def validate(self):
        if len(self.args) < 2:
            raise CommandArgumentError(self, "command must have one object argument and one value argument")            
                      
    @with_session 
    def execute(self, session):        
        
        (spec_string, value) = self.args
        
        resolver = session.spec_parser.parse(spec_string, expected=PropertySpecResolver)
        
        session.begin()
        
        for element_prop in resolver.resolve(session): 
            if not isinstance(element_prop, ElementProperty):
                raise CommandArgumentError("Object Specification does not resolve (point) to an ElementProperty to set: %s" % spec_string)
                                    
            
            if element_prop.is_relation_to_many():
                (operation, value) = (value[0:1], value[1:])
                
                if operation == '=':
                    element_prop.set(value)
                    
                elif operation == '+':
                    element_prop.add(value)
                        
                elif operation == '-':
                    element_prop.remove(value)
                
                else:
                    raise CommandArgumentError(
                    """On OneToMany/ManyToMany relation,first character of new value must be an operator (=, +, -)""")
            
            else:            
                element_prop.set(value)
            
        desc = session.create_change_description()

        if self.option.no_commit:
            self.log.info("no-commit specified: nothing submitted")
        else:
            session.commit()
        
        for change in desc:
            self.log.info(str(change))
            
        self.log.info("Submitted: %s" % session.last_changeset)
        
        