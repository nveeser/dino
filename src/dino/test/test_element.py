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

from dino.db import Element, ResourceElement, ElementFormProcessor
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
    INSTANCE_NAME_ATTRIBUTE = "name"
    
    elixir.using_options(tablename='person')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    name = Field(types.String(20))
    age = Field(types.Integer)
    
    addresses = OneToMany("Address", cascade='all, delete-orphan')
    phone_number = OneToOne("PhoneNumber", cascade='all, delete-orphan')    
    
class Address(Element):    
    elixir.using_options(tablename='address')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    value1 = Field(types.String(20))
    value2 = Field(types.Integer)

    person = ManyToOne('Person')
    
        
    def derive_name(self):
        if self.person is not None:
            return "ADDR-%s-%s" % (self.person.instance_name, self.value1)
            

class PhoneNumber(Element, ResourceElement): 
    INSTANCE_NAME_ATTRIBUTE = 'number'   
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
class ElementTest(DinoTest):
    
    def test_invalid_attr(self):    
        self.failUnlessRaises(RuntimeError, lambda: Person(foo="123"))
            
        
    def test_regex(self):        
        m = Person.element_name_re().match("Person/foo")
    
        self.assertEquals( m.group(1), "Person/foo")
        self.assertEquals( m.group(2), "Person")
        self.assertEquals( m.group(3), "foo")
    
        m = Person.element_name_re().match("Address/foo")
        eq_(m, None)
        
        
class ObjectSpecTest(DinoTest):
    
    def test_element_name_parse(spec):
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
                    'person[;]' ]:        
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

class PersonTest(DatabaseTest):
    ENTITY_SET = entity_set    
    NAME = "eddie"

    def test_basic_name(self):
        p = Person(name=self.NAME, age=12) 
        assert p.derive_name() == self.NAME

       
    def test_store_name(self):        
        sess = self.db.session() 
        
        p = Person(name=self.NAME, age=12)
        sess.add(p)
        sess.flush()
        
        p2 = sess.query(Person).filter_by(instance_name=self.NAME).first()
        
        assert p2.instance_name == self.NAME
        assert p2._instance_name == self.NAME
        
        
        
class AddressTest(DatabaseTest):
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
        self.assertEqual(a2, a)

            
            
class FormDbTest(DataTest, SingleSessionTest):
    ENTITY_SET = entity_set
    DATA_DIR = "element_form"
      
    def test_create_form(self):
        proc = ElementFormProcessor.create(self.sess)
                
        form = self.read_form("person")      
        proc.create_all(form)
                
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"
        eq_(p.age, 12)

        ##################

        form = self.read_form("address")        
        proc.create_all(form)
                
        a = self.sess.find_element("Address/ADDR-eddie-Work")
        eq_(a.person, p)
        
        ##################
        
        form = self.read_form("person_update")
        proc.update_all(form)        
        eq_(len(p.addresses), 0)


    def test_multi_form(self):
        proc = ElementFormProcessor.create(self.sess)
        form = self.read_form("multi")
        proc.create_all(form)
        
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"
        eq_(p.age, 12)
        
        a = self.sess.find_element("Address/ADDR-eddie-Work")
        eq_(a.person, p)

    def test_update_resource(self):
        proc = ElementFormProcessor.create(self.sess)
        
        form = self.read_form("multi")      
        proc.create_all(form)
        
        form = self.read_form("update_resource")      
        proc.update_all(form)
        
        p = self.sess.find_element("Person/eddie")
        assert p is not None, "could not find Person/eddie"


    def read_form(self, formname):
        path = self.get_datafile("%s.form" % formname)        
        return open(path).read()


    def test_dump_form(self):        
        proc = ElementFormProcessor.create(self.sess, show_read_only=False) 

        form = self.read_form("multi")
        proc.create_all(form)
        
        p = self.sess.find_element("Person/eddie")
        
        actual_form = proc.to_form(p)
        
        expected_form = self.read_form("dump")
       
        self.compare_data(expected_form, actual_form)
    
        #eq_(expected_form, actual_form)        

    
