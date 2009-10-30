import sys
import os
import traceback
from pylons import request

from dinoweb.lib.base import *

import dino.cmd as cmd

class ProbeController(DinoCommandController):

    def update(self):
        probe_dir = config['probe_data_dir']
        if not os.path.isdir(probe_dir):
            os.makedirs(probe_dir)

        filepath = os.path.join(config['probe_data_dir'], "%s.yaml" % request.environ['REMOTE_ADDR'])

        probe_form = request.body

        f = open(filepath, 'w')
        f.write(probe_form)
        f.close()

        response.content_type = 'text/plain'

        try:
            command = cmd.DinoCommand.get_command('fimport')(meta.db, self.env)
            opts = command.default_options()
            args = [ filepath ]
            command.execute(opts, args)
            return "\n".join(self.env.output)

        except cmd.CommandError, e:
            response.status = "406"
            output = [ "%s: %s\n" % (e.__class__.__name__, e.msg) ]
            if self.is_traceback():
                output += [ line for line in e.format_trace() ]
            return output

