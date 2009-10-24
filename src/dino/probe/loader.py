#! /usr/bin/env python

'''
configuration and utility information
'''

import sys, os
import atexit

try:
    import json
except ImportError:
    import simplejson as json

import operator
import re
import time
import logging

from dino import class_logger
from dino.probe.error import *

from itertools import ifilter

class ProbeSpecLoader(object):

    def __init__(self, probe_root, probe_override=None):
        self._probe_root = probe_root
        self._spec_root = os.path.join(os.path.dirname(__file__), "probe-spec")
        self.log.info("Find ProbeSpecs: %s" % self._spec_root)


    def find_probe_set(self, name):
        specs = self._load_probe_dict(name)
        self.log.fine("Total Probes: %d", len(specs))
        for s in specs:
            if not s.has_key('sequence'):
                raise LoaderError("Probe has no sequence: %s[%s]" % (s['name'], s['args']))

        specs.sort(key=operator.itemgetter('sequence'))
        return [ProbeSpec(self._probe_root, p) for p in specs]

    @staticmethod
    def find_match(src_probe_spec, probe_dict_list):
        match_name = src_probe_spec['name']
        match_args = src_probe_spec.get('args', None)

        for spec in probe_dict_list:
            if spec['name'] != match_name:
                continue

            if match_args is None:
                return spec

            if spec.has_key('args') and spec['args'] == match_args:
                return spec

        return None

    def _load_probe_dict(self, name):

        data = self._read_data(name)

        my_probes = data['probes']
        self.log.fine("   Probes: %d", len(my_probes))
        if data.has_key("parent"):
            base_probes = self._load_probe_dict(data['parent'])

            for my_probe in my_probes:
                base_probe = self.find_match(my_probe, base_probes)

                if base_probe is None:
                    base_probes.append(my_probe)
                else:
                    for (k, v) in my_probe.items():
                        base_probe[k] = v

            return base_probes
        else:
            return my_probes


    def _read_data(self, name):
        try:
            filename = os.path.join(self._spec_root, "%s.pspec" % name)

            if not os.path.exists(filename):
                raise LoaderError("Could not find probe spec: %s (%s)" % (name, filename))

            self.log.info("Loading: %s" % filename)


            f = open(filename)
            data = f.read()
            f.close()

            return json.loads(data)


        except IOError, ex:
            raise LoaderError(ex)

class_logger(ProbeSpecLoader)


# container object to model a probe
class ProbeSpec(object):

    # probe spec defaults
    DEF_RES_EXPECTED = '.*'
    DEF_RES_CMP = 'any'
    DEF_NO_OUTPUT = 0
    DEF_OK_MSG = 'test passed'
    DEF_ERR_MSG = 'test failed'
    DEF_OK_ACT = 'next'
    DEF_ERR_ACT = 'abort'
    DEF_CACHE_RESULT = 'no'

    # mapping of probe comparators to python methods
    # XXX: assumes first arg is always the expected result
    OP_MAP = {
        'any':    lambda x, y: True,
        'string': operator.eq,
        'match':  lambda x, y: re.match(str(x), str(y)) is not None,
        'bool':   lambda x, y: y,
        'eq':     operator.eq,
        'lt':     operator.eq,
        'le':     operator.le,
        'gt':     operator.gt,
        'ge':     operator.ge,
        'nonzero':  lambda x, y: int(y) != 0,
        'range-in': lambda x, y: int(y) in xrange(int(list(x[0])), int(list(x[1]))),
        'range-out':lambda x, y: int(y) not in xrange(int(list(x[0])), int(list(x[1])))
    }

    def __init__(self, probe_root, d):
        self.probe_root = probe_root
        self.name = d['name']
        self.seq = d['sequence']
        self.cache = d.get('cache_result', ProbeSpec.DEF_CACHE_RESULT)
        self.no_output = int(d.get('no_output', ProbeSpec.DEF_NO_OUTPUT))
        self.exp = d.get('result_expected', ProbeSpec.DEF_RES_EXPECTED)
        self.ok_msg = d.get('pass_comment', ProbeSpec.DEF_OK_MSG)
        self.err_msg = d.get('fail_comment', ProbeSpec.DEF_ERR_MSG)

        # these are functions 
        self.res_cmp = ProbeSpec.OP_MAP[d.get('result_type', ProbeSpec.DEF_RES_CMP)]
        self.ok_act = d.get('pass_action', ProbeSpec.DEF_OK_ACT)
        self.err_act = d.get('fail_action', ProbeSpec.DEF_ERR_ACT)

        # parse args
        self.args = d.get('args', '').split()

    def __str__(self):
        d = {}
        d['name'] = self.name
        d['probe_sequence_id'] = self.seq
        d['cache_result'] = self.cache
        d['no_output'] = self.no_output
        d['result_expected'] = self.exp
        d['pass_comment'] = self.ok_msg
        d['fail_comment'] = self.err_msg
        d['args'] = self.args

        # these are functions 
        d['result_type'] = self.res_cmp
        d['pass_action'] = self.ok_act
        d['fail_action'] = self.err_act

        return str(d)

    def method(self):
         return os.path.join(self.probe_root, self.name)


class ProbeDumper(object):

    def __init__(self, f):
        self.indent = 0
        if isinstance(f, file):
            self.f = f
        elif isinstance(f, basestring):
            self.f = open(f, 'w')
        else:
            raise Exception("huh")

    def write_indent(self, str):
        for i in xrange(0, self.indent): self.f.write(" ")
        self.f.write(str)

    def dump_probe(self, probe, last=False):
        l = [ "\"name\": \"%s\"" % probe['name'] ]

        for name, value in probe.iteritems():
            if name == 'name': continue
            l.append("\"%s\": \"%s\"" % (name, value))

        if not last:
            self.write_indent("{ %s },\n" % ", ".join(l))
        else:
            self.write_indent("{ %s }\n" % ", ".join(l))

    def dump_spec(self, spec_dict):
        self.write_indent("{\n")
        self.indent += 2

        if spec_dict.has_key('parent'):
            self.write_indent('\"parent\": \"%s\",\n' % spec_dict['parent'])

        if spec_dict.has_key('probes'):
            self.write_indent('\"probes\": [\n')

            self.indent += 2
            for probe in spec_dict['probes'][:-1]:
                self.dump_probe(probe)

            self.dump_probe(spec_dict['probes'][-1], last=True)
            self.indent -= 2

            self.write_indent("]\n")

        self.indent -= 2
        self.write_indent("}\n")

