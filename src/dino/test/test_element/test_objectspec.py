
import os
import sys
    
from nose.tools import *

from dino.test.base import *
from dino.test.simplemodel import *

class OldObjectSpec(DinoTest):    
    
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
