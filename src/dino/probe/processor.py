#! /usr/bin/env python

import os,sys
import operator
import stat
import subprocess
import logging
from StringIO import StringIO

from dino import LogObject
from dino.probe.error import *

'''
Primary processing engine for the dino.probe module. This module accepts a list of
probes and runs them in a sequence as defined by the sequence id. 

A probe is dict of the form:
{
    'name': 'name',
    'args': 'space separated args', 
    'probe_sequence_id' : #,
    'no_output': 0,
    'result_type': '',
    'result_expected': '',
    'pass_comment': '',
    'pass_action':'',
    'fail_comment': '',
    'fail_action': ''
}

'''


# processing engine for probes
class Processor(LogObject):
    
    # initialize and check if probe root path is valid
    def __init__(self, probe_specs, check_result=True):
        self._probes = probe_specs
        self.check_result = check_result
                         

    # execute the probes and pre/post exoec files if present
    def run(self):
        results = {}
        for probe in self._probes:     
      
            # check method file location
            if not os.path.exists(probe.method()):
                raise ProcessorError('Probe method %s not found.' % probe.method())
            
            # check if executable, if not make it so
            if os.stat(probe.method()).st_mode & (
                stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH) == 0:
                raise ProcessorError('Probe method is not executable: %s' % probe.method())
            
                
                
            # Run probe method file            
            self.log.info('Processor: executing %s %s' % (
                os.path.basename(probe.method()), ' '.join(probe.args)))
                
            res, out, err = self._exec(probe.method(), probe.args)
            
            probe_output = out.readline().strip()
            self.log.info('Processor: probe output %s' % probe_output)
            if not out.closed:
                out.close()
            if not err.closed:
                err.close()
            
                
            # check results only if needed
            if  self.check_result:
                result = self._check_results(probe, probe_output)
                self.log.info('Processor: probe check result %s' % str(result))
            
                
            # Handle Output
            if probe.no_output == 0:
                probe_key = ('%s %s' % (probe.name, ' '.join(probe.args))).strip()
                results[probe_key] = probe_output                
            else:
                self.log.debug('Processor: output suppression requested')
        
        return results

    # actually executes a probe method
    def _exec(self, cmd, args=[]):
        #print [cmd] + args 
        try:
            proc = subprocess.Popen([cmd] + args, stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, shell=False, env=os.environ)
            self.log.debug("os.environ")
            # wait for it to finish before returning
            ret = proc.wait()
            return ret, proc.stdout, proc.stderr
        except IOError, ex:
            raise ProcessorError(ex, 'Command %s returned and error' % cmd.split()[0])

    # process a success or error action
    def _exec_action(self, probe, result, ok=True):
        if ok:
            (act, msg) = (probe.ok_act, probe.ok_msg)
        else:
            (act, msg) = (probe.err_act,probe.err_msg)
            
        if act == 'next':
            self.log.debug('Processor: action=next, moving on')
            # cache value, if directed.
            if probe.cache != "no":
                self.log.debug('Processor: caching result of %s into %s' % ( probe.name, probe.cache))
                os.environ[probe.cache] = result
            return
        elif act == 'abort':
            self.log.debug('Processor: action=abort, stopping run')
            raise ProcessAbortError('[%s] %s. Expected: %s Got: %s' % (
                probe.name, msg, probe.exp, result))
        else:
            raise ProcessorError('[%s] Invalid action %s' % (probe.name, act))

    # check results based on expected result and operator in probe
    def _check_results(self, probe, result):
        self.log.info('Processor: checking results exp:%s got:%s' % (probe.exp, result))
        if probe.res_cmp(probe.exp, result):
            if probe.ok_act:
                result = self._exec_action(probe, result)
            return probe.ok_msg, result
        else:
            if probe.err_act:
                result = self._exec_action(probe, result, ok=False)
            return probe.err_msg, result




