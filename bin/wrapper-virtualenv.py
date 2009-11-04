#!/mw/app/dino/bin/python

import sys
import os

root = os.path.dirname(__file__)
if os.path.exists(os.path.join(root, ".svn")):
	sys.path[0] = os.path.join(root, "..", "src")

cmdname = os.path.basename(sys.argv[0])

if cmdname in ('dino', 'dinoadm', 'belle', 'pug', 'cli'):
    import dino.cli.admin
    dino.cli.admin.DinoCli().main(sys.argv)

elif cmdname in ('dino-probe'):
    import dino.probe.cli
    dino.probe.cli.ProbeCli().main()

else:
    print "I don't know what I am: ", cmdname

