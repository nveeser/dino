from optparse import Option

import sqlalchemy.orm.properties as sa_props

from dino.config import class_logger
from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import *
#from dino.db.element import *
#from dino.db.exception import *

class AttributeCommand(MainCommand):
    pass
        
class GetCommand(AttributeCommand):
    NAME = "get"
    USAGE = "<ElementName>/<PropertyName>"
    GROUP = "deprecated"
    
    def validate(self):   
        if len(self.args) < 1:
            raise CommandArgumentError(self, "command must have one object argument")            
                
    @with_session 
    def execute(self, session):
        try:  
            aspec = ObjectSpec.parse(self.args[0], expected=AttributeName)      
            
            result = [ attr.value() for attr in aspec.resolve(session) ] 

        except ObjectSpecError, e:
            raise CommandArgumentError(self, str(e))
        except UnknownEntityError, e:
            raise CommandExecutionError(self, e)
        except UnknownElementError, e:
            raise CommandExecutionError(self, e)
        
        if not self.cli:
            return result
            
        for res in result:
            print res


class SetCommand(AttributeCommand):
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

        spec = ObjectSpec.parse(self.args[0], expected=AttributeName)          
        value = self.args[1] 

        session.begin()
        
        for attr in spec.resolve(session):                    
            attr.set(value)
            
        desc = session.create_change_description()

        if self.option.no_commit:
            self.log.info("no-commit specified: nothing submitted")
        else:
            session.commit()
        
        for change in desc:
            self.log.info(str(change))
            
        self.log.info("Submitted: %s" % session.last_changeset)
        
        