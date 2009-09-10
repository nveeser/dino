import os
import sys

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    
from nose.tools import *
from dino.test.base import *

from dino.db.extension import ElementNameBuilder

class TestElementNameBuilder(DinoTest):

    def test_attribute_names(self):
        values = {
            "{mac}_{name}" : set( ('mac', 'name') ), 
            "{port.name}(:{ifindex})" : set( ('ifindex', 'port.name') )  
        }
        
        for k,expected in values.iteritems(): 
            inp = ElementNameBuilder.InstanceNameProcessor(k)
            actual = set(inp.attribute_names)
            eq_(expected, actual)
            
        
    def test_basic_name(self):
        pattern = "{value1}_{value2}"
        
        match_list = (
            ( {'value1' : 'AAA', 'value2' : 'BBB' }, "AAA_BBB" ),
            ( {'value1' : None, 'value2' : 'BBB' }, None ),
            ( {'value1' : 'AAA', 'value2' : None }, None ),
        )
        
        for value_dict, expected in match_list:
            n = ElementNameBuilder.InstanceNameProcessor(pattern)    
            actual = n.make_name(value_dict)
            eq_(expected, actual)


    def test_optional_name(self):
        pattern = "{value1}:{value2}(:{optional1})(_{optional2}X)"    
        match_list = (
            ({'value1' : None, 'value2' : None, 'optional1' : None, 'optional2' : None },  None),        
            ({'value1' : None, 'value2' : None, 'optional1' : None, 'optional2' : '123' },  None),        
            ({'value1' : None, 'value2' : None, 'optional1' : 'ABC', 'optional2' : None },  None),        
            ({'value1' : None, 'value2' : None, 'optional1' : 'ABC', 'optional2' : '123' },  None),        

            ({'value1' : 'val','value2' : None, 'optional1' :  None, 'optional2' : None },  None ),        
            ({'value1' : 'val','value2' : None,  'optional1' : None, 'optional2' : '123' }, None ),  
            ({'value1' : 'val','value2' : None, 'optional1' :  'ABC', 'optional2' : None },  None ),        
            ({'value1' : 'val','value2' : None,  'optional1' : 'ABC', 'optional2' : '123' }, None ),  

            ({'value1' : None, 'value2' : 'thing', 'optional1' : None, 'optional2' : None },  None),        
            ({'value1' : None, 'value2' : 'thing', 'optional1' : None, 'optional2' : '123' },  None),                    
            ({'value1' : None, 'value2' : 'thing', 'optional1' : 'ABC', 'optional2' : None },  None),        
            ({'value1' : None, 'value2' : 'thing', 'optional1' : 'ABC', 'optional2' : '123' },  None),    

            ({'value1' : 'val','value2' : 'thing',  'optional1' : None, 'optional2' : None }, "val:thing" ),  
            ({'value1' : 'val','value2' : 'thing',  'optional1' : None, 'optional2' : '123' }, "val:thing_123X" ),                  
            ({'value1' : 'val','value2' : 'thing',  'optional1' : 'ABC', 'optional2' : None }, "val:thing:ABC" ),  
            ({'value1' : 'val','value2' : 'thing',  'optional1' : 'ABC', 'optional2' : '123' }, "val:thing:ABC_123X" ),  
        )
        
        for i, (value_dict, expected) in enumerate(match_list):
            n = ElementNameBuilder.InstanceNameProcessor(pattern)    
            actual = n.make_name(value_dict)
            eq_(expected, actual, "Issue with test set %d" % i)

    def test_optional_name2(self):
        pattern = "({optional.name}:){value1}"
        match_list = (  
            ({'value1' : None, 'optional.name' : None,  },  None),        
            ({'value1' : None, 'optional.name' : 'ABC',  },  None ),        
            ({'value1' : 'FOO', 'optional.name' : None, },  "FOO"),        
            ({'value1' : 'FOO', 'optional.name' : 'ABC', },  "ABC:FOO"),
        )     
                
        for i, (value_dict, expected) in enumerate(match_list):
            n = ElementNameBuilder.InstanceNameProcessor(pattern)    
            actual = n.make_name(value_dict)
            eq_(expected, actual, "Issue with test set %d  %s was %s" % (i, expected, actual))

