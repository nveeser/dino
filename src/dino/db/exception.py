import sys
import traceback

import sqlalchemy.exc as sa_exc

from dino.exception import DinoException


# # # # # # # # # # # # # # # # # # # 
# Element Exception
# # # # # # # # # # # # # # # # # # # 
class ElementException(DinoException):
    def __init__(self, *args): 
        DinoException.__init__(self, *args)
                        
        if hasattr(self.__class__, "MSG_STR"):
            self.args = args
            try: 
                self.msg = self.MSG_STR % tuple(args)
            except TypeError:
                self.msg = str( (self.MSG_STR,) + tuple(args) )
        else:
            self.msg = args[0]
            self.args = len(args) > 1 and args[1:] or ()        
        
    def __str__(self):
        return self.msg


class DbConfigError(ElementException):
    pass

class InvalidElementClassError(ElementException):
    pass

class ElementExistsError(ElementException):
    pass

    
class ElementNoSessionError(ElementException):
    MSG_STR = "Element has no session: %s"

class ResourceCreationError(ElementException):
    pass

class UnknownEntityError(ElementException):
    MSG_STR = "Unknown Entity: %s"
    def __init__(self, entity_name):
        ElementException.__init__(self, entity_name)
        self.entity_name = entity_name

class UnknownElementError(ElementException):
    MSG_STR = "Could not find specified object: %s"

class ElementInstanceNameError(ElementException):
    pass

class ElementAttributeError(ElementException):
    pass
 
 
class DatabaseError(ElementException):
    '''Used to wrap SQL Alchemy DBAPIError's '''
    def __init__(self, msg, dberr):
        assert isinstance(dberr, sa_exc.DBAPIError)
        self.sa_error = dberr
        self.db_error = dberr.orig
        if self.db_error:
            self.msg = str(self.db_error.args[1])
        else:
            self.msg = str(self.sa_error)
                
        DinoException.__init__(self, self.msg)
                
    def __str__(self):        
        return self.msg
    
    def print_db_error(self):
        if self.db_error:   
            args = [ str(a) for a in self.db_error.args ]
            arg_str = "[ " + ", ".join(args) + " ]"
            msg = "\t%s.%s(%s)" % (self.db_error.__module__, self.db_error.__class__.__name__, arg_str)
        else:
            msg = "\t%s" % e        

        print msg
        print "STATEMENT:\n   %s" % self.sa_error.statement
        print "ARGS:     \n   %s" % str(self.sa_error.params)
        
# # # # # # # # # # # # # # # # # # # 
#  ElementForm Exceptions
# # # # # # # # # # # # # # # # # # #   

class ElementFormException(ElementException):
    pass
    
class UnknownFormPropertyTypeError(ElementFormException):
    pass

class InvalidFormAttributeNameError(ElementFormException):
    pass

class FormTypeError(ElementFormException):
    MSG_STR = "Type mismatch on attribute: %s/%s   Value: %s"

# # # # # # # # # # # # # # # # # # # 
#  ObjectSpec Exceptions
# # # # # # # # # # # # # # # # # # #             
class ObjectSpecError(ElementException):
    def __init__(self, spec, msg):
        self.msg = "'%s': %s" % (str(spec), msg)
        self.args = spec
        
class InvalidObjectSpecError(ObjectSpecError):
    def __init__(self, spec):
        ObjectSpecError.__init__(self, spec, "Invalid ObjectSpec")

class InvalidAttributeError(ObjectSpecError):
    def __init__(self, spec):
        ObjectSpecError.__init__(self, spec, "Invalid Attribute")

class QueryClauseError(ObjectSpecError):
    pass

# # # # # # # # # # # # # # # # # # # 
#  Model Exceptions
# # # # # # # # # # # # # # # # # # # 

class ModelError(ElementException):
    pass
    
class InvalidIpAddressError(ModelError):
    MSG_STR = 'IP is invalid: %s'
    
class ModelArgumentError(ModelError):
    pass

class SchemaVersionMismatch(ModelError):
    MSG_STR = "Version Mismatch: Database (0x%08x) <-> Model (0x%08x)" 
    def __init__(self, schema_info):
        ModelError.__init__(self, schema_info.version, schema_info.model_version)




