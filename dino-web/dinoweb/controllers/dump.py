import sys
from pylons import request

from dinoweb.lib.base import *

class DumpController(BaseController):

    def index(self):
    	c.path = sys.path
        c.dump_obj = dict([ (n, getattr(request, n)) for n in dir(request) ])
        c.environ = request.environ
        return render('/dump.mako')

    def routes(self):
        c.routes = config['routes.map'].matchlist
        return render('/dump/routes.mako')
