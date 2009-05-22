#!/usr/bin/env python

import sys, os
import logging, traceback
from optparse import OptionParser

import dino.config 
from dino.db import DbConfig
from dino import LogObject

class CommandLineInterface(LogObject):
    ''' Interface between the CLI user, and the command/object being executed.
    Handles such user related things as:
    - Logging / Console Output
    - Exception Handling / Formatting
    - CLI Argument Processing
    
    '''

    USAGE = '''
<dino-args> := [ -v ] [ -x ] [ -H <db.host> ] [ -u <db.user> ] [ -p <db.password> ] [ -d <db.name> ]
    -v: move verbose (can use more than one)
    -x: print stack trace on every exception
    -H: database host
    -u: database username
    -p: database password
    -d: database schema/name
    '''


    def __init__(self):
        format = dino.config.load_config("logging").console_format        
        self._basicformatter = logging.Formatter(format)
                        
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setFormatter(self._basicformatter)
        self._console_handler.setLevel(logging.WARNING)        
                
        root = logging.getLogger("")
        root.setLevel(logging.WARNING)
        root.addHandler(self._console_handler)
        
        
    def increase_verbose_cb(self, option, opt, value, parser):
        self.increase_verbose()
        
    def increase_verbose(self):
        level_map = { 
            logging.WARNING : logging.INFO, 
            logging.INFO : logging.FINE,
            logging.FINE : logging.FINER, 
            logging.FINER : logging.FINEST, 
            logging.FINEST : logging.DEBUG, 
            logging.DEBUG : logging.DEBUG
        }

        curr_level = self._console_handler.level   
        for level in level_map.keys():
            if curr_level >= level:
                next_level = level_map[level]
                
        self._console_handler.setLevel(next_level)
        
            
    def setup_base_logger(self, logger_name=""):        
        l = logging.getLogger(logger_name)
        l.propagate = False
        l.addHandler(self._console_handler)
        l.setLevel(logging.DEBUG)
        return l        
            
    def setup_parser(self):
        parser = OptionParser()
        parser.allow_interspersed_args = False    
        parser.add_option("-H", "--host", dest='host', help='database host', default=None)
        parser.add_option("-u", "--user", dest='user', help='database user', default=None)
        parser.add_option("-p", "--password", dest='password', help='database password', default=None)
        parser.add_option("-d", "--database", dest='db', help='database name', default=None)
        parser.add_option('-v', '--verbose', action='callback', callback=self.increase_verbose_cb)
        parser.add_option('-x', '--xception-trace', action='store_true', dest='exception_trace', default=False)
        return parser
    
    def create_db_config(self, cli_options, section=None):
        if section:
            return DbConfig.create(section, options=cli_options)
        else:
            return DbConfig.create(options=cli_options)
            
    
    def main(self, argv):
        raise RuntimeException("NotImplemented")
    
    
    