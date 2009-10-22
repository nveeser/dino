import sys
from pylons import request

import yaml

from dinoweb.lib.base import *

class ProbeController(BaseController):

    def update(self):
        probe_form = request.POST.keys()[0]
        d = yaml.load_all(probe_form)
        for i in d:
            for n, v in i.iteritems():
                print n
        return ""


