#!/usr/bin/env python

import sys
import os
import logging
import traceback
from optparse import OptionParser

import sqlalchemy.exc as sa_exc

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..")


from dino.cli.base import BaseDinoCli
import dino.cmd as cmd
from dino.db import DbConfig, DatabaseError

__all__ = [ 'DinoCli' ]

class DinoCli(BaseDinoCli):

    def prog_usage(self):
        print "for more info: %s help " % self.prog_name()
        print "Usage: %s <dino-args> <Command> [ <command-args> ]" % self.prog_name()
        print self.USAGE
        cmd.DinoCommand.get_command('help').list_commands()

    def prog_name(self):
        return self._prog_name

    def main(self, argv):
        try:
            self._prog_name = os.path.basename(argv[0])
            self.parser = self.setup_parser()
            (options, args) = self.parser.parse_args(args=argv[1:])

            if len(args) < 1:
                self.prog_usage()
                sys.exit(1)

            (cmd_name, args) = (args[0], args[1:])

            db_config = self.create_db_config(options)

            cmd_class = cmd.DinoCommand.get_command(cmd_name)
            command = cmd_class(db_config, self)
            (opts, args) = command.parse(args)
            command.execute(opts, args)

        except cmd.CommandArgumentError, e:
            print "CommandArgumentError: ", e.msg
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
            print "ERROR: ", e.msg

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
    DinoCli().main(sys.argv)

