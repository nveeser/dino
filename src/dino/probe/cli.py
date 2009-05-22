#! /usr/bin/env python

'''
Entry point for hwtest driver
'''

import os,sys
from optparse import OptionParser, OptionError
import logging
import getpass
import simplejson as json

if __name__ == "__main__":
    sys.path[0] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

import dino.config 
from dino.basecli import CommandLineInterface
from dino.probe.driver import Driver
from dino.probe.error import *


LOG_FILE                = '/var/log/probe.log'
FALLBACK_LOG_FILE       = '/tmp/probe.log'
USAGE = 'usage: %prog [-f config]'


class ProbeCli(CommandLineInterface):
    
    def setup_parser(self):
        parser = OptionParser()  
        parser.add_option('-p', '--probe-root', dest='probe_root')
        parser.add_option('-t', '--type-map', dest='type_map')
        parser.add_option('-f', '--filename', dest='filename', default=None)
        parser.add_option('-v', '--verbose', action='callback', callback=self.increase_verbose_cb)
        parser.add_option('-d', '--debug', action='store_true', default=False, help='debug output')
        return parser
        
    
    def setup_logfile(self, root=""):
        try:
            h = logging.FileHandler(LOG_FILE, 'a')
        except IOError,ex:
            print "Opening Fallback log file: %s" % FALLBACK_LOG_FILE
            h = logging.FileHandler(FALLBACK_LOG_FILE, 'a')        
        
        f = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        h.setLevel(logging.DEBUG)
        h.setFormatter(f)
        
        l = logging.getLogger(root)   
        l.setLevel(logging.DEBUG)         
        l.addHandler(h)
        
        if os.environ.has_key('NDEBUG'):
            logging.getLogger("").addHandler(self._console_handler)
            
        return l


    @staticmethod
    def check_root():
        if getpass.getuser() != 'root':
            raise UserNotRootError('You need to be root to run this script.')


    def main(self):
        self.check_root()
        self.setup_base_logger("dino.probe")
        self.setup_logfile("dino.probe")
        parser = self.setup_parser()
        (opts, args) = parser.parse_args()
    
        try:
            driver = Driver(opts.type_map, opts.probe_root)
            results = driver.probe()
            
            
            output = json.dumps(results, sort_keys=True, indent=2) + "\n"
             
            if opts.filename:
                f = open(opts.filename, 'w')
                f.write(output)
                f.close()
            
            else:
                print output 
            
        except ProbeError, ex:
            self.log.error('%s' % ex)
            sys.exit(2)
        


if __name__ == '__main__':
    ProbeCli().main()
