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
        

class PersonTest(DatabaseTest):
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

if __name__ == '__main__':  
    pass

