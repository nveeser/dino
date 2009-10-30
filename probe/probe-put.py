#!/usr/bin/env python

import sys
import os
import httplib
import urllib

from optparse import OptionParser

class PutProbeData(object):
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("-v", dest="verbose", default=0, action="count")
        self.parser.add_option("-x", dest="traceback", default=False, action='store_true')


    def read_file(self, filepath):
        if not os.path.exists(filepath):
            raise Exception("Could not find path: %s" % filepath)

        f = open(filepath)
        data = f.read()
        f.close()
        return data


    def execute(self, args):
        (opts, args) = self.parser.parse_args(args)

        if len(args) != 2:
            raise Exception("Must provide 2 arguments: <host[:port]> <filepath>")

        query = {}
        if opts.verbose != 0:
            query['loglevel'] = opts.verbose
        if opts.traceback:
            query['traceback'] = 1

        (netloc, filepath) = args
        data = self.read_file(filepath)

        conn = httplib.HTTPConnection(netloc)
        conn.request("PUT", "/probe?%s" % urllib.urlencode(query), data)

        res = conn.getresponse()
        if res.status != 200:
            print "ERROR: ", res.status, res.reason

        print res.read()

if __name__ == "__main__":
    PutProbeData().execute(sys.argv[1:])
