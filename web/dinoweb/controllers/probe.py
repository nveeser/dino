import sys
import os
import traceback
from subprocess import Popen, PIPE

from pylons import request

from dinoweb.lib.base import *

import dino.cmd as cmd

class ProbeController(DinoCommandController):

    def update(self):
        if not config.has_key('probe_cache_dir'):
            raise HTTPServerError("dinoweb.ini has missing key: probe_cache_dir")
            #abort(500, )

        if not os.path.isdir(config['probe_cache_dir']):
            os.makedirs(config['probe_cache_dir'])

        filepath = os.path.join(config['probe_cache_dir'], "%s.yaml" % request.environ['REMOTE_ADDR'])

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
            return self.env

        except cmd.CommandError, e:
            response.status = "406"
            output = [ "%s: %s\n" % (e.__class__.__name__, e.msg) ]
            if self.is_traceback():
                output += [ line for line in e.format_trace() ]
            return output

    def download(self):
        response.content_type = 'application/x-gtar'
        response.headers.add('content-disposition', 'filename="probe.tar"')

        p = Popen([ 'tar', '-c', '-f', '-', '-C',
                    config['pylons.paths']['root'], 'probe-tools' ],
            stdout=PIPE, stderr=PIPE)

        (stdout, stderr) = p.communicate()

        if stderr != "":
            raise HTTPServerError(stderr)

        return [ stdout ]

