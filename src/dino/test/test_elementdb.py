#!/usr/bin/env python

import os
import sys
import unittest


if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..")

import dino    

import sqlalchemy
from sqlalchemy import types
from sqlalchemy.orm.collections import attribute_mapped_collection

import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany
from nose.tools import *

from dino.db import Element, ResourceElement, MultiElementFormProcessor, MultiCreateFormProcessor, MultiUpdateFormProcessor
#from dino.db.extension import InstanceNameProcessor 
from dino.db.objectspec import *
from dino.db import collection
from dino.test.base import *

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint




###############################################
#
# Example Classes 
#
__session__ = None
entity_set = __entity_collection__ = collection.EntityCollection()
metadata = __metadata__ = sqlalchemy.schema.MetaData()

from sqlalchemy.orm.collections import collection 

class Person(Element):    
    use_element_name("{name}")
    elixir.using_options(tablename='person')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    name = Field(types.String(20))
    age = Field(types.Integer)
    
    addresses = OneToMany("Address", cascade='all, delete-orphan')
    phone_number = OneToOne("PhoneNumber", cascade='all, delete-orphan')    
    
    
class Address(Element):        
    use_element_name("ADDR-{person.instance_name}-{value1}(:{optional1})")
    elixir.using_options(tablename='address')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    value1 = Field(types.String(20))
    value2 = Field(types.Integer)
    optional1 = Field(types.String(10))

    person = ManyToOne('Person')


class PhoneNumber(Element, ResourceElement): 
    use_element_name("{number}")
    elixir.using_options(tablename='phone_number')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    number = Field(types.String(20))    
    person = ManyToOne("Person")


    @classmethod 
    def create_resource(self, session, value, related_instance=None):
        assert isinstance(related_instance, Person)
        return PhoneNumber(number=value, person=related_instance)
        

#print [ "%s.%s" % (e.__module__, e.__name__) for e in entity_set ]

elixir.setup_entities(entity_set)             


###############################################
#
# UnitTest 
#
from dino.db.objectresolver import *

class TestObjectResolver(DinoTest):
        
    def setUp(self):
        super(TestObjectResolver, self).setUp()        
        self.parser = ObjectSpecParser(entity_set)
       
    

        
    def test_name_type_generator(self):   
               
        def name_type_test(resolver_class, spec):
            parser = ObjectSpecParser(entity_set)
            resolver = parser.parse(spec)            
            ok_(isinstance(resolver, resolver_class))
            
        arg_list = (
            (EntityNameResolver, 'Person'),
            (EntityNameResolver, 'Person/'),
            (EntityNameResolver, 'PhoneNumber'),
            
            (ElementNameResolver, 'Person:name'),
            (ElementNameResolver, 'Person:name/'),
            (ElementQueryResolver, 'Person[foo=bar]'),
            (ElementQueryResolver, 'Person[foo=bar]/'),
            (ElementFormIdResolver, 'Person:<1>'),
            (ElementFormIdResolver, 'Person:<1>/'),
            (ElementIdResovlver, 'Person:{1}'),
            (ElementIdResovlver, 'Person:{1}/'),
            
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

            (ElementIdResovlver, 'Person'),                    
            (ElementIdResovlver, 'Person:name/nothing'),            
            (ElementIdResovlver, 'Person:name'),
            (ElementIdResovlver, 'Person:<1>'),
            (ElementIdResovlver, 'Person[foo=bar]'),
            (ElementIdResovlver, 'Person[foo=bar]/phone_number'),
            (ElementIdResovlver, 'Person[foo=bar]/phone_number/hello2'),

        
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
        r = self.parser.parse('Person/')
        ok_(isinstance(r, EntityNameResolver))    
        eq_(r.get_entity().next(), Person)
        ok_(r.resolve_instance)
                
    @raises(InvalidObjectSpecError)
    def test_entity_name_3(self):
        EntityNameResolver(self.parser, 'NoObject/')
    
    
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
        
    def test_attribute_spec_4(self):
        r = self.parser.parse('Person:instance/addresses/value1')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), None)       

    @raises(InvalidAttributeError)
    def test_attribute_spec_5(self):
        r = self.parser.parse('Person:instance/fake_relation')
        ok_(isinstance(r, AttributeSpecResolver)) 
        eq_(r.get_entity().next(), Address)

    
    def test_entity_spec_special(self):
        r = self.parser.parse('Element')        
        eq_( set((Person, Address, PhoneNumber)), set(r.get_entity()) )
        
        

class TestElement(DinoTest):
    
    @raises(RuntimeError)
    def test_invalid_attr(self):    
        Person(foo="123")
            
        
    def test_regex(self):        
        m = Person.element_name_re().match("Person/foo")
    
        eq_( m.group(1), "Person/foo")
        eq_( m.group(2), "Person")
        eq_( m.group(3), "foo")
    
        m = Person.element_name_re().match("Address/foo")
        eq_(m, None)
        

class TestPerson(DatabaseTest):
    ENTITY_SET = entity_set    
    NAME = "eddie"

    def test_basic_name(self):
        p = Person(name=self.NAME, age=12) 
        assert p.derive_name() == self.NAME

       
    def test_store_name(self):        
        sess = self.db.session() 
        
        p = Person(name=self.NAME, age=12)
        sess.begin()
        sess.add(p)
        sess.commit()
        
        p2 = sess.query(Person).filter_by(instance_name=self.NAME).first()
        
        assert p2.instance_name == self.NAME
                
        
    def test_change_attr(self):
        p = Person(name=self.NAME, age=12)
        p.name = "Bob"        
        assert p.instance_name == "Bob"
        
        
class TestAddress(DatabaseTest):
    ENTITY_SET = entity_set        
    PERSON = 'eddie'
    ADDRESS = "Home"
    ADDRESS_INSTANCE_NAME = "ADDR-eddie-Home"

        
    def test_address_query(self):
        sess = self.db.session() 
        
        p = Person(name=self.PERSON, age=12)         
        a = Address(value1=self.ADDRESS, value2=12, person=p)    

        sess.add(p)                        
        sess.flush()
        
        a2 = sess.query(Address).filter_by(instance_name=self.ADDRESS_INSTANCE_NAME).first()
        eq_(a2, a)

    def test_address_name_dependency(self):
        #print 
        
        sess = self.db.session() 
        
        p = Person(name=self.PERSON, age=12)         
        a = Address(value1=self.ADDRESS, value2=12, person=p)  
                
        sess.add(p)                        
        sess.flush()
        #print "UPDATE"
        p.name = self.PERSON + "ex"        
        
        eq_('ADDR-eddieex-Home', a.instance_name )
        
        
        
class TestFormDb(DataTest, SingleSessionTest):
    ENTITY_SET = entity_set
    DATA_DIR = "element_form"
      
    def test_create_form(self):
        proc = MultiCreateFormProcessor(self.sess)
                
        form = self.read_form("person")     
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
        
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"
        eq_(p.age, 12)

        ##################

        form = self.read_form("address")     
        self.sess.begin()   
        proc.process(form)
        self.sess.commit()
        
        a = self.sess.find_element("Address/ADDR-eddie-Work")
        eq_(a.person, p)
        
        ##################
        
        proc = MultiUpdateFormProcessor(self.sess)
        form = self.read_form("person_update")
        
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
                
        eq_(len(p.addresses), 0)


    def test_multi_form(self):
        proc = MultiCreateFormProcessor(self.sess)
        form = self.read_form("multi")
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
        
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"
        eq_(p.age, 12)
        
        a = self.sess.find_element("Address/ADDR-eddie-Work")
        eq_(a.person, p)

    def test_update_resource(self):
        proc = MultiCreateFormProcessor(self.sess)
        
        form = self.read_form("multi")      
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
        
        proc = MultiUpdateFormProcessor(self.sess)
        form = self.read_form("update_resource")      
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
        
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"


    def read_form(self, formname):
        path = self.get_datafile("%s.form" % formname)        
        return open(path).read()


    def test_dump_form(self):        
        proc = MultiCreateFormProcessor(self.sess, show_read_only=False) 

        form = self.read_form("multi")
        self.sess.begin()
        proc.process(form)
        self.sess.commit()
        p = self.sess.find_element("Person/eddie")
        
        actual_form = proc.to_form(p)
        
        expected_form = self.read_form("dump")
       
        self.compare_data(expected_form, actual_form)
    
        #eq_(expected_form, actual_form)        

if __name__ == '__main__':  
    pass

