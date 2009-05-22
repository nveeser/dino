
import cjson
import simplejson
import os

f = open('verify.pspec')
data = eval(f.read())
f.close()

del data['probes']


def spec_name(type_name, sub_type_name):
    return type_name + '.' + sub_type_name + ".pspec"

def find_similar(type_name, sub_type_map, spec):    
    for other_sub_type_name, other_spec in sub_type_map.items():
        if cmp(spec,other_spec) == 0:
            other_name = spec_name(type_name, other_sub_type_name)
            if os.path.exists(other_name):
                return other_name
        
    return None

def format_output(text):
    for str in [ "\"parent", "\"probes", "]"]:
        text = text.replace(str, "\n    " + str)
    for str in [ "{\"name" ]:
        text = text.replace(str, "\n        %s" % str)
    text = text[0:-1] + "\n}\n"
    return text

for type_name in data.keys():
    sub_type_map = data[type_name]
    for sub_type_name in sub_type_map.keys():
        
        spec = sub_type_map[sub_type_name]
        
        filename = spec_name(type_name, sub_type_name)
        if os.path.exists(filename): os.unlink(filename)
        
        if find_similar(type_name, sub_type_map, spec):
            print "This one is already here: " + other_name
            
        else:
            full_spec = {"parent" : "full", "probes" : spec }
            text = cjson.encode(full_spec)            
            
            print "Write " + filename
            f = open(filename, 'w')
            f.write(format_output(text))
            f.close()