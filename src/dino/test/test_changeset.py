#!/usr/bin/env python

import os,sys
import unittest

import dino   

import sqlalchemy
from sqlalchemy import types
import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany

if __name__ == "__main__":
    sys.path[0] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
from dino.db.changeset import using_changeset
import dino.db.collection
from dino.test.base import *


import pprint; pp = pprint.PrettyPrinter(indent=2).pprint


__session__ = None
__entity_collection__ = entity_set = dino.db.collection.EntityCollection()
__metadata__ = metadata = sqlalchemy.schema.MetaData()


###############################################
#
# Example Classes 
#
class Person(elixir.Entity):
    elixir.using_options(tablename='person')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    name = Field(types.String(20))
    age = Field(types.Integer)
    addresses = OneToMany("Address")

    def __str__(self):
        return "<%s %s(%s)>" % (self.__class__.__name__, self.name, self.age)
    
    
class Address(elixir.Entity):
    elixir.using_options(tablename='address')
    elixir.using_table_options(mysql_engine='InnoDB')
    using_changeset()
    
    value1 = Field(types.String(20))
    value2 = Field(types.Integer)

    person = ManyToOne("Person")    
        
    def __str__(self):
        return "<Addr %s(%s)>" % (self.value, self.prop)


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


#print [ "%s.%s" % (e.__module__, e.__name__) for e in entity_set ]
elixir.setup_entities(entity_set)            


###############################################
#
# UnitTest 
#
###############################################
#    
#class ChangeSetTest(SingleSessionTest):
#    ENTITY_SET = entity_set
#    def tearDown(self):
#                
#        conn = self.db.connection()
#        conn.execute("SET FOREIGN_KEY_CHECKS = 0")
#        for table in ('person', 'person_revision', 'address', 'address_revision'):
#            conn.execute("TRUNCATE TABLE %s" % table)
#        conn.execute("SET FOREIGN_KEY_CHECKS = 1")
#        conn.close()
#        
#        super(ChangeSetTest, self).tearDown()
#        
        
class TestAddEntity(SingleSessionTest):
    ENTITY_SET = entity_set
    
    def test_add_person(self):
       
        self.sess.open_changeset()
        p = Person(name='eddie', age=12)
        self.sess.add(p)
        self.sess.submit_changeset()
        
        assert self.sess.last_changeset is not None
        
        for stmt in ["SELECT * FROM person", "SELECT * FROM person_revision"]:
            result = self.sess.execute(stmt)
        
            rows = result.fetchall()
            assert len(rows) == 1
            myrow = rows[0]
        
            assert myrow['name'] == 'eddie'
            assert myrow['age'] == 12
        
        
    def test_add_address(self):
        self.sess.open_changeset()

        a = Address(value1='Home', value2=12)
        self.sess.add(a)
    
        self.sess.submit_changeset()


    def test_delete_person(self):
        self.sess.open_changeset()
        p = Person(name='eddie', age=12)
        self.sess.add(p)
        self.sess.submit_changeset()
        
        assert self.sess.last_changeset is not None
        
        self.sess.open_changeset()
        self.sess.delete(p)
        cs = self.sess.submit_changeset()
        
        assert cs is not None        
        assert self.sess.last_changeset is not None
        
        result = self.sess.query(Person).filter_by(name='eddie').all()
        
        assert len(result) == 0
        

class TestRevision(SingleSessionTest):     
    ENTITY_SET = entity_set
    
    def setUp(self):
        super(TestRevision, self).setUp()
        
        self.sess.open_changeset()
        p = Person(name='eddie', age=12)
        self.sess.add(p)
        self.sess.submit_changeset()
        
        for i in xrange(4):
            self.sess.open_changeset()
            p.age += 1
            self.sess.submit_changeset()
    
        self.sess.expunge_all()

        
    def test_revision(self):
        
        q = self.sess.query(Person).filter_by(name='eddie').limit(1)
        p = q.first()
        
        assert p.name == 'eddie'
        assert p.revision == 5
        assert p.age == 16
 
    
    def test_revision_query(self):
        
        q = self.sess.query(Person).filter_by(name='eddie').limit(1)
        host = q.first()
        
        rhost = host.get_revision(3)
        assert rhost.revision == 3
        assert hasattr(rhost, '_changeset_view')
        
        
    def test_changeset(self):
        q = self.sess.query(Person).filter_by(name='eddie').limit(1)
        host = q.first()
        
        rhost = host.get_at_changeset(3)
        
        assert rhost.revision == 3
        assert rhost._changeset_view == 3
        
        
    def test_delete(self):
        
        p = self.sess.query(Person).filter_by(name='eddie').first()
        self.sess.open_changeset()
        self.sess.delete(p)
        
        assert p.changeset is not None
        assert self.sess.opened_changeset is not None
        
        cs = self.sess.submit_changeset()        
        assert self.sess.last_changeset is not None
        assert cs is not None
        



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# The following are for development and are not tests
#       
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def do_insert(db):    
    sess = db.session()    
    sess.open_changeset()
    
    print sess.changeset
    for i in range(5):
        name = chr(i + 65)
        value = i
        h = Person(name, i)
        sess.add(h)
        
        a = Address("12.12.12.%d" % i, i)
        h.addresses.append(a)
        a = Address("12.12.12.%d" % (i+100), i)
        h.addresses.append(a)

    cs = sess.submit_changeset()    
    print "Submitted: ", cs
        
    sess.close()
    

def do_updates(db):
    sess = db.session()
    
    rset = sess.query(Person).all()
    
    for x in xrange(10):
        sess.open_changeset()
        for p in rset:
            p.age += 1
            p.addresses[0].value2 += 1
        cs = sess.submit_changeset()
        print "Submitted: " , cs
    
    sess.close()


def do_delete(db):
    sess = db.session()
    sess.open_changeset()
    
    rset = sess.query(Person).filter(Person.name == 'A').limit(1)
    h = rset.first()
    sess.delete(h)
    
    cs = sess.submit_changeset()
    print "Submitted: " , cs
    
    sess.close()


    
#logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

def do_revisions(db):
    sess = db.session()
    
    host = sess.query(Person).filter(Person.name == 'B').limit(1).first()
    
    print host
    rhost = host.get_revision(2)
    print rhost
    for a in rhost.addresses:
        print a
        print a.changeset
        print a.host
        print rhost
        print a.host == rhost
    

    
    
    
    
    
if __name__ == "__main__":
    teardown_module()
    setup_module()
    db = get_database_config(entity_set)
    
    #print db.dump_schema()
    do_insert(db)
    #do_updates(db)
    #do_delete(db)
    #do_revisions(db)
    
