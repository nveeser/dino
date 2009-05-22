#!/usr/bin/env python

import os, sys
import simplejson as json

_cache = {}
def load_spec(file):
    global _cache
    
    if not _cache.has_key(file):
        _cache[file] = json.load(open("%s" % file))
    
    return _cache[file]



def find_probe(spec, name):
    for probe in spec['probes']:
        if probe['name'] == name:
            return probe

def clean_child_parent(parent_spec, child_spec):
    
    child_probes = child_spec['probes']
    child_spec['probes'] = []
    
    for child_probe in child_probes:
        parent_probe = find_probe(parent_spec, child_probe['name']) 
        
        for key in child_probe.keys():
            #print parent_probe['name'] + ":" + key
            
            if parent_probe.has_key(key): 
                if child_probe[key] == parent_probe[key]:
                    #print "Delete key: %s" % key
                    del child_probe[key]
                else:
                    pass#print "Not the same [%s] [%s]" % (child_probe[key], parent_probe[key])
            
                
        if len(child_probe) > 0:
             child_probe['name'] = parent_probe['name']
             child_spec['probes'].append(child_probe)


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
        for i in xrange(0,self.indent): self.f.write(" ")        
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

    def dump_spec(self, spec):            
        self.write_indent("{\n")        
        self.indent += 2
        
        if spec.has_key('parent'):
            self.write_indent('\"parent\": \"%s\",\n' % spec['parent'])
            
        if spec.has_key('probes'):
            self.write_indent('\"probes\": [\n')
            
            self.indent += 2            
            for probe in spec['probes'][:-1]:
                self.dump_probe(probe)
                      
            self.dump_probe(spec['probes'][-1], last=True)
            self.indent -= 2
                        
            self.write_indent("]\n")
        
        self.indent -= 2
        self.write_indent("}\n")
        
        
def main():
    full_spec = load_spec("full.pspec") 
    for probe in full_spec['probes']:
        probe['result_expected'] = ".*"
    
    
    for file in os.listdir("."):
        if not file.endswith(".pspec"): continue
        
        print "Processing: %s" % file
        child_spec = load_spec(file)
        
        if not child_spec.has_key('parent'):  continue
    
        parent_spec = load_spec("%s.pspec" % child_spec['parent'])  

        clean_child_parent(parent_spec, child_spec)
        
        dumper = ProbeDumper("./%s" % file)
        dumper.dump_spec(child_spec)    
    
    
    dumper = ProbeDumper("./full.pspec")
    dumper.dump_spec(full_spec)    
    
        
main()