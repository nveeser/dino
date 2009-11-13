from dino.cmd import DinoCommand
from dino.command import CommandArgumentError


class InfoCommand(DinoCommand):
    ''' Specify the help string (doc string) for a given command or schema object'''

    NAME = "info"
    USAGE = ""
    GROUP = "system"
    ASSERT_SCHEMA_VERSION = False


    def execute(self, opts, args):
        info = self.db_config.schema_info
        self.cmd_env.write("DB API URL: %s" % self.db_config.uri)
        if info is None:
            self.cmd_env.write("No Database Version information could be found")
        else:
            self.cmd_env.write("DB Version:    %02X" % info.database_version)
            self.cmd_env.write("Model Version: %02X" % info.model_version)
