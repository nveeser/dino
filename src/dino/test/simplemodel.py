import os
import sys
import unittest

import dino    

import sqlalchemy
from sqlalchemy import types
from sqlalchemy.orm.collections import attribute_mapped_collection

import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany

from nose.tools import *

import dino.db.collection as collection  
from dino.db import *

###############################################
#
# Example Classes 
#
__session__ = None
entity_set = simple_entity_set = __entity_collection__ = collection.EntityCollection()
metadata = __metadata__ = sqlalchemy.schema.MetaData()

__all__ = [ 'simple_entity_set', 'Company', 'Person', 'Address', 'PhoneNumber' ]


class Company(Element):
    use_element_name("{name}")
    elixir.using_options(tablename='company')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    name = Field(types.String(20))
    value1 = Field(types.Integer)
    
    employees = OneToMany("Person", cascade='all')




class Person(Element):    
    use_element_name("{name}")
    elixir.using_options(tablename='person')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    name = Field(types.String(20))
    age = Field(types.Integer)
    
    company = ManyToOne('Company')
    addresses = OneToMany("Address", cascade='all, delete-orphan')
    phone_number = OneToOne("PhoneNumber", cascade='all, delete-orphan')    
    
    
    
class Address(Element):        
    use_element_name("ADDR-{person.instance_name}-{value1}(:{optional1})")
    elixir.using_options(tablename='address')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    value1 = Field(types.String(20))
    value2 = Field(types.Integer)
    optional1 = Field(types.String(10))

    person = ManyToOne('Person')


class PhoneNumber(Element, ResourceElement): 
    use_element_name("{number}")
    elixir.using_options(tablename='phone_number')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    number = Field(types.String(20))    
    person = ManyToOne("Person")


    @classmethod 
    def create_resource(self, session, value, related_instance=None):
        assert isinstance(related_instance, Person)
        return PhoneNumber(number=value, person=related_instance)
        

########
# Experiment with inheritance
########

class Car(elixir.Entity):
    elixir.using_options(tablename='car')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    color = Field(types.String(255), index=True)
    mileage = Field(types.Integer)  

class Sedan(Car):
    pass 

class Suv(Car):
    fourwheeldrive = Field(types.Boolean, default=False)
    

elixir.setup_entities(entity_set)             





