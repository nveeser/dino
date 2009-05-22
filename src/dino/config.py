import sys,os
import logging
from ConfigParser import RawConfigParser
from optparse import OptionParser

log = logging.getLogger("dino.config")

LOCATIONS = [
    "%(pkg_path)s/dino.cfg",   # Package defaults 
    "/etc/dino.cfg", "/etc/dino/dino.cfg",  # Host defaults
    "%(home)s/.dino.cfg" # User defaults
    ]

var_map = { 
    'pkg_path' : os.path.abspath(os.path.dirname(__file__)),
    'home' : os.path.abspath(os.environ['HOME']),
}


class setattrable_dict(dict):
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__

    
CFG = None
def load_config(section=None):
    global CFG
    if not CFG:
        CFG = RawConfigParser()        
        filenames =  [ l % var_map for l in LOCATIONS ]
        log.debug("Files (start): %s" % filenames)
        read_files = CFG.read(filenames)                
        log.debug("Files (done): %s" % read_files)
    
    if section:
        if not CFG.has_section(section):
            return None
        
        settings = setattrable_dict()
        for name, value in CFG.items(section):
            setattr(settings, name, value)
        return settings
    else:
        return CFG    


def config_logging():
    file_config = load_config()
        
    if file_config.has_section("logging"):
        for opt in file_config.options("logging"):
            levelname = file_config.get('logging', opt)
            level = logging.getLevelName(levelname)            
            logging.getLogger(opt).setLevel(level)
            

def class_logger(cls, level=None):
    logger = logging.getLogger(cls.__module__ + "." + cls.__name__)
    cls.log = logger


config_logging()

    
if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter(indent=2).pprint    
    cfg = load_config()
    pp(cfg)