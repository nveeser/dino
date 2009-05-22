#! /usr/bin/env python

import cjson
import pprint

from dino.probe.error import *
from dino.probe.exporter.dataexporter import DataExporter

# file system based exporter of results
class FileExporter(DataExporter):

    def _do_open(self):
        try:
            self._stream = open(self._export_uri, 'w')
        except IOError, ex:
            raise ExportError(ex)

    def _do_report(self, data):
        try:
            # make it pretty - replace with jsonlib
            data = pprint.pformat(data, indent=2)
            data = data.replace("'", '"')
            self._stream.write('%s\n' % data)
            return 0
        except IOError, ex:
            raise ExportError(ex)

    def _do_close(self):
        debug('FileExporter: closing sink')
        try:
            self._stream.close()
        except IOError, ex:
            raise ExportError(ex)
