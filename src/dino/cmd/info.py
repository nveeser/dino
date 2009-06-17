from dino.cmd import MainCommand
from dino.cmd.exception import CommandArgumentError


class InfoCommand(MainCommand):
    ''' Specify the help string (doc string) for a given command or schema object'''
    
    NAME = "info"
    USAGE = ""
    GROUP = "system"
    
    def execute(self):
        
        info = self.db_config.schema_info
        print "DB API URL: %s" % self.db_config.uri 
        if info is None:
            print "No Database Version information could be found"
        else:
            print "DB Version:    %02X" % info.database_version
            print "Model Version: %02X" % info.model_version