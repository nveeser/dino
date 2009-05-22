import sys
from dino.exception import DinoException


# # # # # # # # # # # # # # # # # # # # #
#
# Command Exceptions
# 
# # # # # # # # # # # # # # # # # # # # #

class CommandError(DinoException):
    def __init__(self, msg, code=-1, cause=None):
        DinoException.__init__(self, msg, code)
        self.msg = msg
        self.code = code 
            
    def __str__(self):
        return str(self.msg)
        
class CommandDefinitionError(CommandError):
    '''Thrown when there is an error in the definition of a Command Class'''

class ArgumentError(CommandError):
    ''' Error in any argument passed to the CLI'''

class InvalidCommandError(CommandError):
    '''Command does not exist'''
    def __init__(self, name):
        CommandError.__init__(self, "Invalid Command: " + name)

class CommandExecutionError(CommandError):
    '''Error during execute of a specific command'''
    def __init__(self, command, msg, code=-1):
        self.command = command
        CommandError.__init__(self, msg, code)
    
    def __str__(self):
        if self.__cause__:
            return "CommandExecutionError: %s" % self.__cause__
        else:
            return"CommandExecutionError: ", self.msg
    
class CommandArgumentError(CommandExecutionError):
    ''' Error in an argument passed to a command'''
    
    
   