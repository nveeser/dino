
from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *
from dino.cmd.jsonutil import *
from dino.db.objectspec import *

class JsonExportCommand(MainCommand):

    '''Query repository for a complete server description.'''

    NAME = "jsonexport"
    USAGE = "<object> Host/<InstanceName>"
    GROUP = "data"

    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, 'Please specify a server in fqdn format.\n')
        if len(self.args) >= 2: 
            raise CommandArgumentError(self, 'You can specify ONLY ONE server.\n')

    @with_session 
    def execute(self, session):
             
        name = self.args[0].split('.')
        if len(name) != 3: 
            raise CommandArgumentError(self, 'Host does not have the proper fqdn format.')
            
        processor = JsonProcessor(session)
    
        oname = ObjectSpec.parse(self.args[0], expected=ElementName)
        
        if oname.entity_name != "Host":
            raise CommandArgumentError(self, "ElementName is not a Host: %s" % str(oname))
    
        host = session.find_element(oname)        
        
     	json = processor.host_to_json(host)
                
        if self.cli is None:
            return json
    
        print json        
        
    
