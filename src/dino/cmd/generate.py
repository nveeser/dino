from optparse import Option

from dino.cmd.command import DinoCommand
from dino.cmd.exception import *

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

    def execute(self):
        if self.cmd_env:
            self.cmd_env.setup_base_logger("dino.generate")

        if self.option.list:
            for g in Generator.generator_class_iterator():
                print g.NAME
            return


        if len(self.args) > 0:
            classes = [ Generator.get_generator_class(name) for name in self.args ]
        else:
            classes = Generator.generator_class_iterator(exclude='dns')

        generator_settings = self.cmd_env.get_config("generate")

        try:

            gen_list = [ c(self.db_config, generator_settings) for c in classes ]

            for gen in gen_list:
                gen.parse(self.args)

            if self.option.generate:
                for gen in gen_list:
                    gen.generate()

            if self.option.compare:
                for gen in gen_list:
                    gen.compare()

            if self.option.activate:
                for gen in gen_list:
                    gen.activate()

            if not self.option.generate and not self.option.compare and not self.option.activate:
                for gen in gen_list:
                    gen.generate()

                for gen in gen_list:
                    gen.activate()

        except NoSuchGeneratorError, e:
            raise CommandArgumentError(self, str(e))

        except GeneratorException, e:
            raise CommandExecutionError(self, e)
