import os
import sys

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    
from nose.tools import *

from dino.test.base import *
from dino.test.simplemodel import entity_set, Company, Person, Address, PhoneNumber

from dino.db.objectresolver import ObjectSpecParser, EntityNameResolver, ElementNameResolver, \
    ElementIdResolver, ElementFormIdResolver, AttributeSpecResolver, \
    ElementQueryResolver, SpecMatchError

class TestObjectResolver(DinoTest):
        
    def setUp(self):
        super(TestObjectResolver, self).setUp()        
        self.parser = ObjectSpecParser(entity_set)
       
                
            
    def test_element_name_regex(self):
                 
        def name_match_test(entity, spec, results):
            m = entity.element_name_regex().match(spec)
            assert_not_equal(m, None)
            eq_(results, m.groups())
            
        args_list = (         
            (Person, 'Person:name', ('Person:name', 'Person', 'name')),            
            (Person, 'Person:something:1', ('Person:something:1', 'Person', 'something:1')),
            (Person, 'Person:<1>', ('Person:<1>', 'Person', '<1>')),
            (Person, 'Person:{2}', ('Person:{2}', 'Person', '{2}')),
            (Address, 'Address:<1>', ('Address:<1>', 'Address', '<1>')),
        )
        
        for args in args_list:  
            yield (name_match_test, ) + args  
            
        
    def test_name_type_generator(self):   
               
        def name_type_test(resolver_class, spec):
            parser = ObjectSpecParser(entity_set)
            resolver = parser.parse(spec)            
            ok_(isinstance(resolver, resolver_class))
            
        arg_list = (
            (EntityNameResolver, 'Person'),
            (EntityNameResolver, 'Person:'),
            (EntityNameResolver, 'PhoneNumber'),
            
            (ElementNameResolver, 'Person:name'),
            (ElementNameResolver, 'Person:name/'),
            (ElementNameResolver, 'Person:name:1'),
            (ElementQueryResolver, 'Person[foo=bar]'),
            (ElementQueryResolver, 'Person[foo=bar]/'),
            (ElementFormIdResolver, 'Person:<1>'),
            (ElementFormIdResolver, 'Person:<1>/'),
            (ElementIdResolver, 'Person:{1}'),
            (ElementIdResolver, 'Person:{1}/'),
            
            (AttributeSpecResolver, 'Person:name/phone_number'),
            (AttributeSpecResolver, 'Person:name/phone_number/number'),
            (AttributeSpecResolver, 'Person[foo=bar]/phone_number'),
            (AttributeSpecResolver, 'Person[foo=bar]/phone_number/number'),
        )
        
        for args in arg_list: 
            yield (name_type_test,) + args   
        
    def test_name_mismatch_generator(self):   
         
        @raises(SpecMatchError)        
        def name_mismatch_test(class_, spec):
            parser = ObjectSpecParser(entity_set)
            class_(parser, spec)
            
        args_list = (         
            (EntityNameResolver, 'Person:name/phone_number'),            
            (EntityNameResolver, 'Person:{1}'),
            (EntityNameResolver, 'Person:<1>'),
            (EntityNameResolver, 'Person:name'),
            (EntityNameResolver, 'Person[foo=bar]'),
            (EntityNameResolver, 'Person[foo=bar]/phone_number'),
            (EntityNameResolver, 'Person[foo]/phone_number/hello2'),
            
            (ElementNameResolver, 'Person'),                    
            (ElementNameResolver, 'Person:name/nothing'),            
            (ElementNameResolver, 'Person:{1}'),
            (ElementNameResolver, 'Person:<1>'),
            (ElementNameResolver, 'Person[foo=bar]'),
            (ElementNameResolver, 'Person[foo=bar]/phone_number'),
            (ElementNameResolver, 'Person[foo=bar]/phone_number/hello2'),

            (ElementIdResolver, 'Person'),                    
            (ElementIdResolver, 'Person:name/nothing'),            
            (ElementIdResolver, 'Person:name'),
            (ElementIdResolver, 'Person:<1>'),
            (ElementIdResolver, 'Person[foo=bar]'),
            (ElementIdResolver, 'Person[foo=bar]/phone_number'),
            (ElementIdResolver, 'Person[foo=bar]/phone_number/hello2'),

        
            (ElementFormIdResolver, 'Person'),            
            (ElementFormIdResolver, 'Person:name/nothing'),            
            (ElementFormIdResolver, 'Person:instance_name'),
            (ElementFormIdResolver, 'Person:{1}'),
            (ElementFormIdResolver, 'Person[foo=bar]'),
            (ElementFormIdResolver, 'Person[foo=bar]/phone_number'),
            (ElementFormIdResolver, 'Person[foo=bar]/phone_number/hello2'),
        
            (AttributeSpecResolver, 'Person'),            
            (AttributeSpecResolver, 'Person:instance_name'),
            (AttributeSpecResolver, 'Person:<1>'),
            (AttributeSpecResolver, 'Person:{1}'),
            (AttributeSpecResolver, 'Person[foo=bar]'),
        )        
        for args in args_list:  
            yield (name_mismatch_test, ) + args    

                
    def test_entity_name_1(self):
        r = self.parser.parse('Person')
        ok_(isinstance(r, EntityNameResolver))    
        eq_(r.get_entity().next(), Person)
        ok_(not r.resolve_instance)
    
    def test_entity_name_2(self):
        r = self.parser.parse('Person:')
        ok_(isinstance(r, EntityNameResolver))    
        eq_(r.get_entity().next(), Person)
        ok_(r.resolve_instance)
                
    @raises(InvalidObjectSpecError)
    def test_entity_name_3(self):
        EntityNameResolver(self.parser, 'NoObject:')
    
    
    def test_element_name_1(self):
        r = self.parser.parse('Person:instance')
        ok_(isinstance(r, ElementNameResolver))        
        ok_(isinstance(r.parent_resolver, EntityNameResolver))
                
        eq_(r.get_entity().next(), Person)
        eq_(r.instance_name, "instance")
        ok_(not r.resolve_instance)

        
    def test_element_name_2(self):
        r = self.parser.parse('Person:instance/')
        ok_(isinstance(r, ElementNameResolver))        
        ok_(isinstance(r.parent_resolver, EntityNameResolver))
                
        eq_(r.get_entity().next(), Person)
        eq_(r.instance_name, "instance")        
        ok_(r.resolve_instance)


    def test_attribute_spec_1(self):
        r = self.parser.parse('Person:instance/age')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), None)

    @raises(InvalidObjectSpecError)
    def test_attribute_spec_2(self):
        r = self.parser.parse('Person:instance/age/')

    def test_attribute_spec_3(self):
        r = self.parser.parse('Person:instance/addresses')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), Address)
    
    def test_attribute_spec_3(self):
        r = self.parser.parse('Person:instance/addresses[0]')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), Address)
        
    def test_attribute_spec_5(self):
        r = self.parser.parse('Person:instance/addresses/value1')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), None)       


    @raises(InvalidAttributeSpecError)
    def test_attribute_spec_fail_1(self):
        r = self.parser.parse('Person:instance/fake_relation')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), Address)

    @raises(InvalidObjectSpecError)
    def test_attribute_spec_fail_2(self):
        r = self.parser.parse('Person/instance_name')
        
    @raises(InvalidObjectSpecError)
    def test_attribute_spec_fail_3(self):
        r = self.parser.parse('Person/instance_name/age[0]')

    @raises(InvalidObjectSpecError)
    def test_attribute_spec_fail_4(self):
        r = self.parser.parse('Person/instance_name/phone_number[0]')

    def test_entity_spec_special(self):
        r = self.parser.parse('Element')        
        eq_( set((Company, Person, Address, PhoneNumber)), set(r.get_entity()) )
        
    

