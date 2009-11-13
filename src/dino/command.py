from optparse import OptionParser

from dino.exception import DinoException



class CommandMeta(type):
    ''' 
    Meta-Class to create a series of Command Classes, and find 
    them via a common Base Class
    '''
    def __init__(cls, name, bases, dict_):
        super(CommandMeta, cls).__init__(name, bases, dict_)

        # If this class's base class is not a CommandMeta class 
        # (ie the base's metaclass is something other than CommandMeta), 
        # then this class is the 'Root'. Add the Dictionaries
        base_class_type = type(bases[0])
        if not issubclass(base_class_type, CommandMeta):
            cls.COMMANDS = {}
            cls.GROUPS = {}

        if not hasattr(cls, 'NAME'):
            raise CommandDefinitionError("CommandMeta Instance has no NAME attribute: %s" % name)

        # NAME is None means the Command is abstract and 
        # should not be included in the list of commands
        if cls.NAME is None:
            return

        if isinstance(cls.NAME, (list, tuple)):
            for name in cls.NAME:
                cls.COMMANDS[name] = cls
        else:
            cls.COMMANDS[cls.NAME] = cls

        if hasattr(cls, 'GROUP'):
            cls.GROUPS.setdefault(cls.GROUP, []).append(cls)
        else:
            cls.GROUPS.setdefault('other', []).append(cls)

        cls.parser = OptionParser()
        if hasattr(cls, 'OPTIONS'):
            opts = getattr(cls, 'OPTIONS')
            assert isinstance(opts, (tuple, list)), "%s.OPTIONS must be a tuple or list" % name
            for opt in opts:
                cls.parser.add_option(opt)


    #
    # Find/Get All Commands
    #
    def commands(cls):
        return cls.COMMANDS.values()

    def has_command(cls, key):
        return cls.COMMANDS.has_key(key)

    def find_command(cls, key):
        ''' Find a command, return None if not found'''
        try:
            return cls.get_command(key)
        except InvalidCommandError:
            return None

    def get_command(cls, key):
        ''' Find a command, raise exception if not found'''
        if cls.COMMANDS.has_key(key):
            return cls.COMMANDS[key]
        else:
            raise InvalidCommandError(key)


class Command(object):
    ''' 
    Used by Classes which use the CommandMeta metaclass. 
    '''

    __metaclass__ = CommandMeta

    NAME = None

    def __init__(self, cmd_env=None):
        assert isinstance(cmd_env, AbstractCommandEnvironment), "context is not correct type: %s" % type(cmd_env)
        self.cmd_env = cmd_env

    @property
    def prog_name(self):
        if self.cmd_env:
            return self.cmd_env.prog_name()
        else:
            return "PROG_NAME"

    def parse(self, args):
        ''' Parse arguments on command '''

    def validate(self, opts, args):
        ''' Should be implemented to validate command line options '''

    def execute(self, opts, args, **kwargs):
        '''Execute Command'''
        raise NotImplemented()

    def print_usage(self):
        '''print single line usage about the command'''

    def print_help(self):
        '''print multi-line help about the command'''


class AbstractCommandEnvironment(object):

    def write(self, msg=""):
        print(msg)

    def prog_name(self):
        return "Unknown"

    def setup_base_logger(self, logger_name=""):
        pass

    def increase_verbose(self):
        pass

    def increase_verbose_cb(self, option, opt, value, parser):
        pass

    def get_config(self, section=None):
        pass


class CommandError(DinoException):
    def __init__(self, msg, code= -1, cause=None):
        DinoException.__init__(self, msg, code)
        self.msg = msg
        self.code = code

    def __str__(self):
        return str(self.msg)

class CommandDefinitionError(CommandError):
    '''Thrown when there is an error in the definition of a Command Class'''

class ArgumentError(CommandError):
    ''' Error in any argument passed to the CLI'''

class CommandExecutionError(CommandError):
    '''Error during execute of a specific command'''
    def __init__(self, command, msg, code= -1):
        self.command = command
        CommandError.__init__(self, msg, code)

    def __str__(self):
        if self.__cause__:
            return "CommandExecutionError: %s" % self.__cause__
        else:
            return"CommandExecutionError: %s" % self.msg

class CommandArgumentError(CommandExecutionError):
    ''' Error in an argument passed to a command'''


class InvalidCommandError(CommandError):
    '''Command does not exist'''
    def __init__(self, name):
        CommandError.__init__(self, "Invalid Command: " + name)





class CommandWithClassSubCommand(Command):
    '''
    Command which delegates to sub commands implemented as a hierarchy of command classes
    
    prog mycmd mysub -arg -arg
    
    -> 
    
    class MyCommand(CommandWithClassSubCommand):
        NAME = "mycmd"
        
    MyBaseSubCommand = MyCommand.get_base_subcommand()
    
    class MySubCommand(MyBaseSubCommand):
        NAME = 'mysub'
        
        def execute(self, opts, args):
            ...
        
    '''
    NAME = None
    USAGE = ""
    SUBCOMMAND_CLASS = None

    @classmethod
    def get_base_subcommand(cls):
        if not cls.SUBCOMMAND_CLASS:
            cls.SUBCOMMAND_CLASS = cls.create_base_subcommand()

        return cls.SUBCOMMAND_CLASS

    @classmethod
    def create_base_subcommand(cls):
        class BaseSubCommand(object):
            '''Base Class of all subcommands'''
            NAME = None
            MAIN_COMMAND = cls

            __metaclass__ = CommandMeta

            def __init__(self, parent, cmd_env=None):
                self.parent = parent
                self.cmd_env = cmd_env

            @property
            def prog_name(self):
                if self.cmd_env:
                    return self.cmd_env.prog_name()
                else:
                    return "PROG_NAME"

            def validate(self, opts, args):
                pass

            def parse(self, args):
                return self.parser.parse_args(args=args)

            def execute(self, opts, args):
                raise NotImplemented()

            def print_usage(self):
                self.log.info(self.prog_name + " " + self.MAIN_COMMAND.NAME + " " + self.NAME + " " + self.USAGE)

            def print_help(self):
                self.log.info("   ", self.__class__.__doc__)

        return BaseSubCommand

    def execute(self, opts, args):
        if self.SUBCOMMAND_CLASS is None:
            raise CommandExecutionError(self, "SubCommand improperly defined")

        if len(args) < 1:
            raise CommandArgumentError(self, "Must specifiy a subcommand")

        cmd_name = args.pop(0)
        cmd_class = self.SUBCOMMAND_CLASS.get_command(cmd_name)
        print cmd_class
        cmd = cmd_class(self, self.cmd_env)
        (opts, args) = cmd.parse(args)
        cmd.validate(opts, args)
        return cmd.execute(opts, args)


    def print_help(self):
        if self.SUBCOMMAND_CLASS is None:
            raise CommandExecutionError(self, "SubCommand improperly defined")

        print "Sub-Commands: "
        for cmd_class in self.SUBCOMMAND_CLASS.commands():
            cmd = cmd_class(self, self.cmd_env)
            cmd.print_usage()
            cmd.print_help()





class CommandWithMethodSubCommand(Command):
    '''
    Command with subcommands implemented as methods
    
    prog mycmd mysub -arg -arg
    
    -> 
    
    class MyCommand(CommandWithMethodSubCommand):
        NAME = "mycmd"
        
        def sub_mysub(self):
            do_stuff()
            
        
    '''
    NAME = None
    USAGE = ""

    def execute(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, "Must specify a subcommand")
        (subcmd, args) = (args[0], args[1:])

        if hasattr(self, 'sub_' + subcmd):
            meth = getattr(self, 'sub_' + subcmd)
            return meth(opts, args)
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



