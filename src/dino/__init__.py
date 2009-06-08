import sys
import os
import logging

#
# Major Hack to get around multiple installs of package sqlalchemy
# Should be using pkg_resources.py
#
eggs = [ "SQLAlchemy-0.5.3-py2.4.egg", "SQLAlchemy-0.5.3-py2.6.egg"]
for p in sys.path[:]:
    for egg in eggs: 
        fullname = os.path.join(p, egg)
        if os.path.exists(fullname):
            sys.path.insert(sys.path.index(p), fullname)

sys.path.insert(0, "/mnt/hgfs/nicholas/Documents/workspace/SQLAlchemy-0.5.3/lib/")

import sqlalchemy
if sqlalchemy.__version__ != "0.5.3":
    raise RuntimeException("Found wrong version of SqlAlchemy: %s" % sqlalchemy.__version__)


def get_class_logger(cls):
    return logging.getLogger(cls.__module__ + "." + cls.__name__)

#logging.get_class_logger = get_class_logger


class LogObjectMeta(type):
    def __init__(cls, name, bases, dict_):
        super(LogObjectMeta, cls).__init__(name, bases, dict_) 
        cls.log = get_class_logger(cls)
        
class LogObject(object):
    __metaclass__ = LogObjectMeta


METHOD_TEMPLATE = """\
def _log_method(self, msg, *args, **kwargs):
    level = %s
    if self.manager.disable >= level:
        return
    if level >= self.getEffectiveLevel():
        self._log(level, msg, args, **kwargs)
"""     

# 20 INFO
# 18 FINE
# 16 FINER
# 14 FINEST
# 10 DEBUG
def setup_logging_levels():
    # Just for the fun of it, add new logging levels to the infrastructure
    for (level, name) in ((14, 'FINEST'), (16, 'FINER'), (18, 'FINE')):
        logging.addLevelName(level, name)
        setattr(logging, name, level)
        
        exec METHOD_TEMPLATE % level 
        _log_method.func_name = name.lower()
        
        setattr(logging.Logger, _log_method.func_name, _log_method)

    
setup_logging_levels()
