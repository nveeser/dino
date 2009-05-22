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
        print "DB Version:    %02X" % info.version
        print "Model Version: %02X" % info.model_version