import sys
import logging
from pylons import request

from dinoweb.lib.base import *

class DumpController(DinoCommandController):

    def index(self):
    	c.path = sys.path
        c.dump_obj = dict([ (n, getattr(request, n)) for n in dir(request) ])
        c.environ = request.environ
        return render('/dump.mako')

    def routes(self):
        c.routes = config['routes.map'].matchlist
        return render('/dump/routes.mako')


    def logging(self):
        self.env.setup_base_logger("dino.cmd")

        log_dict = dict((n, (l, []))
            for n, l in logging.Logger.manager.loggerDict.iteritems()
                if isinstance(l, logging.Logger))

        log_dict["root"] = (logging.Logger.root, [])

        for l, children in log_dict.values():
            if l.parent:
                parent = l.parent.name
                log_dict[parent][1].append(l.name)

        c.log_data = log_dict
        return render('/dump/logging.mako')
