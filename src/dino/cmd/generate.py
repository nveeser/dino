from optparse import Option

from dino.cmd.command import DinoCommand
from dino.command import *

from dino.generators.base import Generator, NoSuchGeneratorError, GeneratorException

from dino.db import DbConfig, DbConfigError

class GenerateCommand(DinoCommand):
    ''' Run Generator(s) for various services '''
    NAME = ("generate", "gen")
    USAGE = "{ -l | [ <generator> [ <generator> ] ... ] [ -g | -a ] }"
    GROUP = "data"

    OPTIONS = (
        Option('-g', '--generate', dest='generate', action='store_true', default=False),
        Option('-c', '--compare', dest='compare', action='store_true', default=False),
        Option('-a', '--activate', dest='activate', action='store_true', default=False),
        Option('-l', '--list', dest='list', action='store_true', default=False),
    )

    @classmethod
    def print_help(cls, args=None):
        print
        print "Generators:"
        for g in Generator.generator_class_iterator():
            print "   ", g.NAME

    def execute(self, opts, args):
        if self.cmd_env:
            self.cmd_env.setup_base_logger("dino.generate")

        if opts.list:
            for g in Generator.generator_class_iterator():
                print g.NAME
            return

        generator_settings = self.cmd_env.get_config("generate")

        if len(args) > 0:
            classes = [ Generator.get_generator_class(name) for name in args ]

        elif generator_settings.get('default_generators'):
            names = map(lambda s: s.strip(), generator_settings.get('default_generators').split(','))
            classes = [ c for c in Generator.generator_class_iterator() if c.NAME in names ]

        else:
            classes = Generator.generator_class_iterator(exclude=('dns', 'pxe'))


        try:

            gen_list = [ c(self.db_config, generator_settings) for c in classes ]

            for gen in gen_list:
                gen.parse(args)

            if opts.generate:
                for gen in gen_list:
                    gen.generate()

            if opts.compare:
                for gen in gen_list:
                    gen.compare()

            if opts.activate:
                for gen in gen_list:
                    gen.activate()

            if not opts.generate and not opts.compare and not opts.activate:
                for gen in gen_list:
                    gen.generate()

                for gen in gen_list:
                    gen.activate()

        except NoSuchGeneratorError, e:
            raise CommandArgumentError(self, str(e))

        except GeneratorException, e:
            raise CommandExecutionError(self, e)
