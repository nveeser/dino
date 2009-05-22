#! /usr/bin/env python

'''
Base class for all exporters: defines primary interfaces only

subclasses need to implement:
def _do_open(self)
def _do_report(self, data)
def _close(self)
'''

import os
import logging

from dino.probe.error import *

class DataExporter(object):
    log = logging.getLogger("dino.probe.DataExporter")
    
    def __init__(self, export_uri):
        self.log.info('DataExporter: exporting to %s' % os.path.basename(export_uri))
        self._export_uri = export_uri
        self._closed = True
        self._stream = None

    def report(self, data):
        if len(data) == 0:
            raise ExportError('Zero length data cannot be exported.')
        self._open()
        res = self._do_report(data)
        self._close()
        debug('DataExporter: exported to %s' % os.path.basename(self._export_uri))
        return res

    def _open(self):
        if self._closed:
            self._do_open()
            self._closed = False

    def _close(self):
        if not self._closed:
            self._do_close()
            self._closed = True

    def _do_open(self):
        raise NotImplementedError("")

    def _do_report(self, data):
        raise NotImplementedError("")

    def _do_close(self):
        raise NotImplementedError("")
