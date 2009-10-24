#!/usr/bin/env python

import sys, os
import logging, traceback
from optparse import OptionParser
from ConfigParser import RawConfigParser

from dino import class_logger
from dino.cli.log import LogController
from dino.command import AbstractCommandEnvironment
from dino.db import DbConfig

class setattrable_dict(dict):
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__


class DinoFileConfiguration(dict):
    CONFIG_SEARCH_PATH = [
        "%(pkg_path)s/dino.cfg", # Package defaults 
        "/etc/dino.cfg", "/etc/dino/dino.cfg", # Host defaults
        "%(home)s/.dino.cfg" # User defaults
    ]

    def __init__(self):
        var_map = {
            'pkg_path' : os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
            'home' : os.path.abspath(os.environ['HOME']),
        }
        parser = RawConfigParser()
        filenames = [ l % var_map for l in self.CONFIG_SEARCH_PATH ]
        self.log.debug("Files (start): %s" % filenames)
        read_files = parser.read(filenames)
        self.log.debug("Files (done): %s" % read_files)

        for section in parser.sections():
            self[section] = setattrable_dict()
            for name, value in parser.items(section):
                self[section][name] = value

    def get_config(self, section=None):
        if section:
            return self.get(section, None)
        else:
            return self

class_logger(DinoFileConfiguration)


class BaseCommandEnvironment(AbstractCommandEnvironment):

    def __init__(self):
        self._configuration = DinoFileConfiguration()
        self._log_controller = LogController()
        self._log_controller.reset()
        self._log_controller.configure(self._configuration.get_config("logging"))

    def get_config(self, section=None):
        return self._configuration.get_config(section)

    def increase_verbose_cb(self, option, opt, value, parser):
        self._log_controller.increase_verbose()

    def increase_verbose(self):
        self._log_controller.increase_verbose()

    def setup_base_logger(self, logger_name=""):
        return self._log_controller.setup_base_logger(logger_name)


class BaseDinoCli(BaseCommandEnvironment):
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

    def create_db_config(self, cli_options, section='db'):
        file_config = self.get_config(section)
        if file_config is None:
            raise DbConfigError("Cannot find file section: %s" % section)

        cli_options = dict((key, getattr(cli_options, key))
            for key in ('host', 'user', 'password', 'db') if getattr(cli_options, key))

        return DbConfig.create_from_dict(file_config, **cli_options)

    def main(self, argv):
        raise RuntimeException("NotImplemented")

class_logger(BaseDinoCli)


