import logging
from optparse import OptionParser

from dino.cmd.exception import *

__all__ = [ 
    'AbstractCommandInterface', 'CommandMeta',  
    'with_session', 'with_connection' 
]

class AbstractCommandInterface(object):        
    ''' Abstract Command Interface 
    Used by Classes which use the CommandMeta metaclass. 
    '''

    def __init__(self, cli=None):
        self.cli = cli
     
    @property
    def prog_name(self):
        if self.cli:
            return self.cli.prog_name
        else:
            return self.PROG_NAME

    def parse(self, args):   
        ''' Parse arguments on command '''             
       
    def execute(self):
        '''Execute Command'''
        raise NotImplemented()

    def validate(self):
        ''' Should be implemented to validate command line options '''

    def print_usage(self):
        '''print single line usage about the command'''
        
    def print_help(self):
        '''print multi-line help about the command'''


class CommandMeta(type): 
    def __init__(cls, name, bases, dict_):
        super(CommandMeta, cls).__init__(name, bases, dict_) 
        
        cls.log = logging.getLogger("dino.cmd." + name)
        
        
        # If this class's base class is not a CommandMeta class 
        # (ie the base's metaclass is something other than CommandMeta), 
        # then this class is the 'Root'. Add the Dictionaries
        base_class_type = type(bases[0])
        if not issubclass( base_class_type, CommandMeta ): 
            cls.COMMANDS = {}
            cls.GROUPS = {}      
        
        if not hasattr(cls,'NAME'):
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
    def has_command(cls, key):        
        return cls.COMMANDS.has_key(key)
 
    def find_command(cls, key):
        ''' Find a command, return None if not found'''
        if cls.COMMANDS.has_key(key):
            return cls.COMMANDS[key]
        else:
            return None
             
    def get_command(cls, key):
        ''' Find a command, raise exception if not found'''
        cmd = cls.find_command(key)
        if cmd is None:
            raise InvalidCommandError(key)        
        return cmd

    def commands(cls):
        return cls.COMMANDS.values()
        



#
# Decorators for Command Execution
#    
def with_session(func):
    '''decorator for methods that need a session'''
    def session_func(self):
        session = None
        try:
            self.log.finer("open session")
            session = self.db_config.session()
            return func(self, session)
        finally:     
            if session:        
                self.log.finer("close session")   
                session.close()
    session_func.__doc__ = func.__doc__
    return session_func

def with_connection(func):
    '''decorator for methods that need a connection'''
    def connection_func(self):
       
        connection = None
        try:                
            self.log.finer("open connection")
            connection = self.db_config.connection()
            return func(self, connection)
        finally:     
            if connection:    
                self.log.finer("close connection")       
                connection.close()
    connection_func.__doc__ = func.__doc__
    return connection_func



