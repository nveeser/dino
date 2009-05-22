#!/usr/bin/env python

import sys
import os
import logging
import traceback
from optparse import OptionParser

import sqlalchemy.exc as sa_exc

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..")


import dino.cmd as cmd
from dino.db import DatabaseError
from dino.basecli import CommandLineInterface

class AdminCli(CommandLineInterface):

    
    def prog_usage(self):
        print "for more info: %s help " % self.prog_name
        print "Usage: %s <dino-args> <Command> [ <command-args> ]" % self.prog_name
        print self.USAGE
        cmd.MainCommand.get_command('help').list_commands()

 
    def main(self, argv):
        try:
            self.prog_name = os.path.basename(argv[0]) 
            self.parser = self.setup_parser()   
            (options, args) = self.parser.parse_args(args=argv[1:])
                  
            log = self.setup_base_logger("dino.cmd")  
          
            if len(args) < 1:
                self.prog_usage()                
                sys.exit(1)
             
                
            db_config = self.create_db_config(options)
            log.info("DBConfig: %s" % db_config.uri)
                            

            cmd.MainCommand.prog_name = argv[0]    
            cmd_name = args[0]
            args = args[1:]
    
            
            cmd_class = cmd.MainCommand.get_command(cmd_name)
            command = cmd_class(db_config, self)
            command.parse(args)        
            command.execute()
        
        except cmd.CommandArgumentError, e:
            print "CommandArgumentError: ", e.message
            print
            e.command.print_usage()
            if options.exception_trace: e.print_trace()
            sys.exit(e.code)
    
        except cmd.CommandExecutionError, e: 
            print str(e)

            for cause, tb in e: 
                if isinstance(cause, DatabaseError):
                    cause.print_db_error()
                
            if options.exception_trace: e.print_trace()
            sys.exit(e.code)
            
        except cmd.CommandError, e:
            print "ERROR: ", e.message
              
            if options.exception_trace: e.print_trace()
            sys.exit(e.code)
            
        except KeyboardInterrupt, e:
            print "Ctrl-C"
            sys.exit(1)
        except SystemExit, e:
            pass
        except Exception, e:
            mname = hasattr(e, '__module__') and "%s." % e.__module__ or ""
            print "Unknown Error: %s%s" % (mname, e.__class__.__name__)
            print e
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    AdminCli().main(sys.argv)


    
