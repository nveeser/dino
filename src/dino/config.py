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



class LogController(object):
    def __new__(cls, *args, **kwargs):
        if '_instance' not in vars(cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):                        
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.DEBUG)   

        self.root = logging.getLogger("")
        self.root.setLevel(logging.WARNING)
        self.root.addHandler(self.console_handler)
        
        self.load_config()

    def reset(self):
        self.console_handler.setLevel(logging.WARNING)   

    def load_config(self):
        file_config = load_config() 
        if file_config.has_section("logging"):
            for opt in file_config.options("logging"):
                levelname = file_config.get('logging', opt)
                level = logging.getLevelName(levelname)
                logging.getLogger(opt).setLevel(level)
                
            format = load_config("logging").console_format        
            self._basicformatter = logging.Formatter(format)
            self.console_handler.setFormatter(self._basicformatter)
            
                    
    def increase_verbose(self):
        level_map = { 
            logging.WARNING : logging.INFO, 
            logging.INFO : logging.FINE,
            logging.FINE : logging.FINER, 
            logging.FINER : logging.FINEST, 
            logging.FINEST : logging.DEBUG, 
            logging.DEBUG : logging.DEBUG
        }
    
        curr_level = self.console_handler.level   
        for level in level_map.keys():
            if curr_level >= level:
                next_level = level_map[level]
                
        self.console_handler.setLevel(next_level)

    def setup_base_logger(self, logger_name=""):        
        l = logging.getLogger(logger_name)
        l.propagate = False
        l.addHandler(self.console_handler)
        l.setLevel(logging.DEBUG)
        return l  

LogController()

def class_logger(cls, level=None):
    logger = logging.getLogger(cls.__module__ + "." + cls.__name__.lower())
    cls.log = logger


if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter(indent=2).pprint    
    cfg = load_config()
    pp(cfg)