import types
import logging

from dino import class_logger
import dino.cmd
from dino.cmd.exception import *
from dino.db import ElementException, DatabaseError, SchemaVersionMismatch
from dino.command import *


# # # # # # # # # # # # # # # # # # # # #
#
# Root Command Class
# 
# # # # # # # # # # # # # # # # # # # # #        
class DinoCommandMeta(CommandMeta):
    '''
    Add to the basic command setup
    - logging for commands
    - Exception wrapper / translation
    '''

    LOG_ROOT = "dino.cmd."

    def __init__(cls, name, bases, dict_):
        super(DinoCommandMeta, cls).__init__(name, bases, dict_)

        # Add logging to all commands
        cls.log = logging.getLogger(DinoCommandMeta.LOG_ROOT + name.lower())

        # Add wrapper for catching model exceptions
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


class DinoCommand(Command):
    ''' Root Command object 
    All Command objects are derived from here.  The Command <-> name mapping is contained here.
    '''
    __metaclass__ = DinoCommandMeta

    NAME = None
    ASSERT_SCHEMA_VERSION = True

    def __init__(self, db_config, cmd_env=None):
        Command.__init__(self, cmd_env)
        self.db_config = db_config
        if self.cmd_env:
            self.cmd_env.increase_verbose()  # make INFO the default log level

        self.cmd_env.setup_base_logger("dino.cmd")
        #self.log.fine("DBConfig: %s" % self.db_config.uri)

        if self.cmd_env and not self.parser.has_option("-v"):
                self.parser.add_option('-v', '--verbose', action='callback', callback=self.cmd_env.increase_verbose_cb)

        if self.ASSERT_SCHEMA_VERSION:
            try:
                self.db_config.assert_schema_version()
            except SchemaVersionMismatch, e:
                raise CommandExecutionError(self, e)


    def parse(self, args):
        (opts, args) = self.parser.parse_args(args=args)
        self.validate(opts, args)
        return (opts, args)

    def validate(self, options, args):
        pass

    def print_usage(self):
        if isinstance(self.NAME, (list, tuple)):
            self.cmd_env.write(self.prog_name + " " + self.NAME[0] + " " + self.USAGE)
        else:
            self.cmd_env.write(self.prog_name + " " + self.NAME + " " + self.USAGE)

    def print_help(self):
        pass

class_logger(DinoCommand)

#
# Decorators for Command Execution
#    
def with_session(func):
    '''decorator for methods that need a session'''
    def session_func(self, *args, **kwargs):
        session = None
        try:
            self.log.finer("open session")
            args = args + (self.db_config.session(),)
            return func(self, *args, **kwargs)
        finally:
            if session:
                self.log.finer("close session")
                session.close()
    session_func.__doc__ = func.__doc__
    session_func.__orig__ = func
    return session_func

def with_connection(func):
    '''decorator for methods that need a connection'''
    def connection_func(self, *args, **kwargs):

        connection = None
        try:
            self.log.finer("open connection")
            args += (self.db_config.connection(),)
            return func(self, *args, **kwargs)
        finally:
            if connection:
                self.log.finer("close connection")
                connection.close()
    connection_func.__doc__ = func.__doc__
    return connection_func




