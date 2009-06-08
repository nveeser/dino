#! /usr/bin/env python

'''
Driver for hardware testing on hosts. It takes a config file with data source
and data export information, runs the tests and exports the results.
'''

import os
import logging
try:
    import json
except ImportError:
    import simplejson as json

from dino import LogObject
from dino.probe.processor import Processor
from dino.probe.error import *
from dino.probe.loader import ProbeSpecLoader

DEFAULT_HW_TYPE = "unknown unknown"

class Driver(LogObject):
        
    def __init__(self, type_map_file=None, probe_root=None):
        
        if type_map_file is None:
            type_map_file = self._find_path("probe-spec/type_map.json")
            
        self.log.debug('using type_map: %s' % type_map_file)          
        self._type_map = self._read_type_map(type_map_file)       

        if probe_root is None:
            probe_root = self._find_path("probe-exec")           
             
        self.log.debug('using probe root: %s' % probe_root)          
        self._loader = ProbeSpecLoader(probe_root)        


    def probe(self):
        
        probe_specs = self._loader.find_probe_set("identify")
        
        result = Processor(probe_specs, check_result=False).run()
        
        result = self._identify_hw_type(result)
    
        self.log.debug('Driver: check result = %s' % result)
        if len(result) == 0:
            raise UnknowHardwareError('Could not determine hardware type')
        
        self.log.info('check results %s' % result)
        (hw_type, hw_sub_type) = result.split()
        
        
        (os.environ['MW_MODEL_NAME'], os.environ['MW_HNODE_TYPE_DICT']) = (hw_type,hw_sub_type)
                
        spec_name = "%s.%s" % (hw_type,hw_sub_type)
        probe_specs = self._loader.find_probe_set(spec_name)
        
        return Processor(probe_specs, check_result=True).run()



    def report(self, data):
        res = 0
        for exporter in self._exporters:
            res |= exporter.report(data)
        return res

    def _find_path(self, path):
        path = os.path.join(os.path.dirname(__file__), path)            
        if os.path.exists(path):
            return path 
        else:
            raise ConfigError("Can't find path: %s" % path)
        
    def _read_type_map(self, map_file):
        self.log.info("read file: %s" % map_file)
        f = open(map_file, 'r')
        try:
            return json.loads(f.read())
        finally:
            f.close()

    def _identify_hw_type(self, results):        
        for type in self._type_map:
            if self._type_map[type] == results:
                return type
        
        return DEFAULT_HW_TYPE

