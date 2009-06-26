None#!/usr/bin/env python

import os
import sys

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..")

from nose.tools import *

from dino.db.extension import ElementNameBuilder
from dino.db.objectspec import *
from dino.test.base import *

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint





class NameParseTest(DinoTest):

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

class ObjectSpecTest(DinoTest):    
    
    def test_element_name_parse(self):
        x = ObjectSpec.parse('person/foo')
        eq_( x.entity_name, 'person' )
        eq_( x.instance_name, 'foo')
    
    def test_element_name_type(self):        
        for spec in [ 'person/foo', 'Chassis/ss', 'Object/x' ]:        
            oname = ObjectSpec.parse(spec)
            eq_(type(oname), ElementName)
            
    def test_element_id_type(self):        
        for spec in [ 'person/{2}' ]:        
            oname = ObjectSpec.parse(spec)
            eq_(type(oname), ElementId)

    def test_element_form_id_type(self):        
        for spec in [ 'person/<12>' ]:        
            oname = ObjectSpec.parse(spec)
            eq_(type(oname), ElementFormId)

    def test_attribute_name_parse(spec):
        x = ObjectSpec.parse('person/foo/attr')
        eq_( x.entity_name, 'person' )
        eq_( x.instance_spec, 'foo')
        eq_( x.property_name, 'attr')
        
    def test_attribute_name_type(self):        
        for spec in [ 'person/foo/attr' ]:        
            x = ObjectSpec.parse(spec)
            eq_(type(x), AttributeName)
        
    def test_element_query_parse(spec):
        x = ObjectSpec.parse('person[name=foo]')
        eq_( x.entity_name, 'person' )
        eq_( x.query_clause, 'name=foo')
        
    def test_element_query_type(self):        
        for spec in [ 'person[name=foo]', 
                    'person[name=foo;car=bar]', 
                    'person[;]',
                    'host[name=unknown-2q1u1co]' ]: 
                               
            x = ObjectSpec.parse(spec)
            eq_(type(x), ElementQuery)

    def test_attribute_query_parse(spec):
        x = ObjectSpec.parse('person[name=foo]/attr', expected=AttributeName)
        eq_( x.entity_name, 'person' )
        eq_( x.element_spec.query_clause, 'name=foo')
        
    def test_attribute_query_type(self):        
        for spec in [ 'person[name=foo]/attr', 
                      'person[name=foo;car=bar]/attr',
                      'person[;]/something',
                      'person[]/something'  ]:        
            x = ObjectSpec.parse(spec)
            eq_(type(x), AttributeName)
            eq_(type(x.element_spec), ElementQuery)
    
    @raises(ObjectSpecError)
    def test_fail_type1(self):
        x = ObjectSpec.parse('person[name=foo]/attr', expected=ElementQuery)
        
    @raises(ObjectSpecError)
    def test_fail_type2(self):
        x = ObjectSpec.parse('person[name=foo]/attr', expected=(ElementQuery, ElementName))

    def test_is_type(self):
        for x in ['person/foo', 'person/{1}', 'person/<2>']:
            assert_true(ElementSpec.is_spec(x), "Does not match: %s" % x )
    
    def test_is_type2(self):
        for x in ['person/foo', 'person/{1}', 'person/<2>']:
            assert_true(ObjectSpec.is_spec(x), "Does not match: %s" % x )

    def test_is_type_fail(self):
        for x in ['person/foo', 'person/{1}', 'person/<2>']:
            assert_true(AttributeSpec.is_spec(x), "Does not match: %s" % x )
