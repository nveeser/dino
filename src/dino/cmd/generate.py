from optparse import Option

from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.generators.base import Generator, NoSuchGeneratorError, GeneratorException

from dino.db import DbConfig, DbConfigError

class GenerateCommand(MainCommand):
    ''' Run Generator(s) for various services '''
    NAME = ("generate", "gen")
    USAGE = "{ -l | [ <generator> [ <generator> ] ... ] [ -g | -a ] }"
    GROUP = "data"
    
    OPTIONS = ( 
        Option('-g', dest='generate', action='store_true', default=False), 
        Option('-a', dest='activate', action='store_true', default=False), 
        Option('-l', dest='list', action='store_true', default=False), 
    )
        
    @classmethod
    def print_help(cls, args=None):
        print
        print "Generators:"
        for g in Generator.generator_class_iterator():
            print "   ", g.NAME
    
    def execute(self):
        if self.cli:
            self.cli.setup_base_logger("dino.generate")        
        
        if self.option.list:
            for g in Generator.generator_class_iterator():
                print g.NAME
            return

    
        if len(self.args) > 0:
            classes = [ Generator.get_generator_class(name) for name in self.args ]
        else:
            classes = Generator.generator_class_iterator(exclude='dns')    
    
        try:
            gen_db_config = DbConfig.create(section="generator.db")
        except DbConfigError, e:
            self.log.fine("Falling back to main db config")
            gen_db_config = self.db_config
            
            
        try:
        
            gen_list = [ c(gen_db_config) for c in classes ] 
            
            for gen in gen_list:
                gen.parse(self.args)
                
            if self.option.generate:
                for gen in gen_list:
                    gen.generate()
                    
            elif self.option.activate:
                for gen in gen_list:
                    gen.activate()
                                    
            else:
                for gen in gen_list:
                    gen.generate()
                
                for gen in gen_list:
                    gen.activate()
        
        except NoSuchGeneratorError, e:
            raise CommandArgumentError(self, str(e))

        except GeneratorException, e:
            raise CommandExecutionError(self, e)