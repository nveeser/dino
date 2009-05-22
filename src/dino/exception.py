import sys
import traceback

class DinoException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)        
        
        if sys.exc_info()[1] is not None:
            self.__cause__ = sys.exc_info()[1]
            self.__cause_traceback__ = sys.exc_info()[2]
        else:
            self.__cause__ = None 
            self.__cause_traceback__ = None
            
    
    def __iter__(self):
        e = self
        while hasattr(e, '__cause__') and e.__cause__ is not None:
            yield e.__cause__, e.__cause_traceback__
            e = e.__cause__   
        return 
        
    def print_trace(self, e=None):
        print
        print "TRACEBACK"        
        self._print_exception(self, sys.exc_info()[2])
        
        for cause, cause_tb in self:
            self._print_exception(cause, cause_tb)
        
    def _print_exception(self, e, tb):
        print
        print "%s.%s: %s" % (e.__module__, e.__class__.__name__, str(e))
        traceback.print_tb(tb)   
    