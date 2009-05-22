import types


from dino.cmd.command import CommandMeta, AbstractCommandInterface
from dino.cmd.exception import *
from dino.db import ElementException, DatabaseError

# # # # # # # # # # # # # # # # # # # # #
#
# Root Command Class
# 
# # # # # # # # # # # # # # # # # # # # #        
class MainCommandMeta(CommandMeta):
    def __init__(cls, name, bases, dict_):
        super(MainCommandMeta, cls).__init__(name, bases, dict_) 
              
        # Add wrapper for catching model exceptions
        #
        cls.execute = cls._execute_decorator(cls.execute)
    

    @staticmethod
    def _execute_decorator(func):
        ''' Wrap all execute methods with this decorator, which is 
        used to handle exceptions more uniformily '''
        
        def execute_decorator_func(self, *args, **kwargs):
            try:                
                return func(self, *args, **kwargs)
                          
            except ElementException, e:
                self.log.fine("Converting ElementException to CommandExecuteError")
                raise CommandExecutionError(self, "Caught Error during Command Execution:")
                
        return execute_decorator_func


class MainCommand(AbstractCommandInterface):
    ''' Root Command object 
    All Command objects are derived from here.  The Command <-> name mapping is contained here.
    '''
    __metaclass__ = MainCommandMeta

    NAME = None
    PROG_NAME = "dino"

    def __init__(self, db_config, cli=None):
        AbstractCommandInterface.__init__(self, cli)
        self.db_config = db_config
        if self.cli:
            self.cli.increase_verbose()  # make INFO the default log level
                
        
    def parse(self, args):                
        if self.cli and not self.parser.has_option("-v"):
                self.parser.add_option('-v', '--verbose', action='callback', callback=self.cli.increase_verbose_cb)
        (self.option, self.args) = self.parser.parse_args(args=args)        
        self.validate()

    def print_usage(self):
        if isinstance(self.NAME, (list, tuple)):
            print self.prog_name + " " + self.NAME[0] + " " + self.USAGE
        else:
            print self.prog_name + " " + self.NAME + " " + self.USAGE

    def print_help(self):
        pass


 


class ClassSubCommand(MainCommand):
    NAME = None
    USAGE = ""
    SUBCOMMAND_CLASS = None
    
    @staticmethod
    def set_subcommand(main_cmd_class, sub_cmd_class):
        main_cmd_class.SUBCOMMAND_CLASS = sub_cmd_class
        sub_cmd_class.MAIN_COMMAND_NAME = main_cmd_class.NAME

    def parse(self, args): 
        if self.cli and not self.parser.has_option("-v"):
                self.parser.add_option('-v', '--verbose', action='callback', callback=self.cli.increase_verbose_cb)
        self.args = args               
    
    def execute(self):        
        if self.SUBCOMMAND_CLASS is None:
            raise CommandExecutionError(self, "SubCommand improperly defined")
        
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specifiy a subcommand")

        cmd_name = self.args.pop(0)
        cmd_class = self.SUBCOMMAND_CLASS.get_command(cmd_name)
        cmd = cmd_class(self.db_config, self.cli)
        cmd.parse(self.args)
        cmd.validate()
        return cmd.execute()

    
    def print_help(self):
        if self.SUBCOMMAND_CLASS is None:
            raise CommandExecutionError(self, "SubCommand improperly defined")
        
        print "Sub-Commands: "
        for cmd_class in self.SUBCOMMAND_CLASS.commands():    
            cmd = cmd_class(self.db_config, self.cli)            
            cmd.print_usage()
            cmd.print_help()   


        
 
class MethodSubCommand(MainCommand):
    NAME = None
    USAGE = ""
    
    
    def execute(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specify a subcommand")
        (subcmd, self.args) = (self.args[0], self.args[1:])
        
        if hasattr(self, 'sub_' + subcmd):
            meth = getattr(self, 'sub_' + subcmd)
            return meth()
        else:
            raise CommandArgumentError(self, "Unknown subcommand: " + subcmd)
  
        
    def print_help(self):                
        for x in dir(self.__class__):
            if not x.startswith("sub_"):
                continue
                
            attr = getattr(self, x)
            if type(attr) == types.MethodType:
                cmdname = x[4:]
                doc = attr.im_func.func_doc                    
                print "%s: - %s" % (cmdname, doc)
                    

