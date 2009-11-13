
from dino.cmd.command import with_session, DinoCommand
from dino.command import *
from dino.cmd.jsonutil import *
from dino.db import ElementNameResolver
class JsonExportCommand(DinoCommand):

    '''Query repository for a complete server description.'''

    NAME = "jsonexport"
    USAGE = "<object> Host/<InstanceName>"
    GROUP = "data"

    def validate(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, 'Please specify a server in fqdn format.\n')
        if len(args) >= 2:
            raise CommandArgumentError(self, 'You can specify ONLY ONE server.\n')

    @with_session
    def execute(self, opts, args, session):

        name = args[0].split('.')
        if len(name) != 3:
            raise CommandArgumentError(self, 'Host does not have the proper fqdn format.')

        processor = JsonProcessor(self, session)

        resolver = session.spec_parser.parse(args[0], expected=ElementNameResolver)

        for elmt in resolver.resolve(session):
            json = processor.host_to_json(elmt)

        self.cmd_env.write(json)


