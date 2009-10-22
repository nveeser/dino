#!/mw/dino/bin/python

import sys
import os


#class Importer(object):
#    def find_module(self, fullname, path=None):
#        print "SEARCH: ", fullname, path
#        return None  
#          
#sys.meta_path.append(Importer())

cmdname = os.path.basename(sys.argv[0])

if cmdname in ('dino', 'dinoadm', 'belle', 'pug', 'cli'):
    import dino.cmd.cli
    dino.cmd.cli.AdminCli().main(sys.argv)

elif cmdname in ('dino-probe'):
    import dino.probe.cli
    dino.probe.cli.ProbeCli().main()

else:
    print "I don't know what I am: ", cmdname

