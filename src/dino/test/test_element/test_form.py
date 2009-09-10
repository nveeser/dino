import os
import sys

from nose.tools import *

from dino.test.base import *
from dino.test.simplemodel import *

from dino.db.element_form import *


class TestForm(DataTest, SingleSessionTest):
    ENTITY_SET = simple_entity_set
    DATA_DIR = "element_form"



class TestFormSingle(TestForm):
 
    def test_create_form(self):
        print 
        proc = MultiElementFormProcessor(self.sess, allow_create=True)
          
        self.sess.begin()   
        form = self.read_form("person")     
        proc.process(form)
        self.sess.commit()
                
        p = self.sess.find_element("Person:eddie")
        assert p is not None, "could not find Person:eddie"
        eq_(p.age, 12)
        eq_(len(p.addresses), 0)

        ##################

        self.sess.begin()   
        form = self.read_form("address")     
        proc.process(form)
        self.sess.commit()
        
        a = self.sess.find_element("Address:ADDR-eddie-Work")
        eq_(a.person, p)
        
       
        
        ##################
        
        proc = MultiElementFormProcessor(self.sess)
        
        self.sess.begin() 
        form = self.read_form("person_update")        
        proc.process(form)
        self.sess.commit()
                
        eq_(len(p.addresses), 0)


class TestFormMulti(TestForm):

    def setUp(self):
        self.setUpClass()        
        super(TestFormMulti, self).setUp()
        
        
        sess = self.db.session()
        
        sess.begin() 
        proc = MultiElementFormProcessor(sess, allow_create=True)
        form = self.read_form("multi")
        proc.process(form)
        sess.commit()


    def tearDown(self):
        self.tearDownClass()        
        super(TestFormMulti, self).tearDown()
        
    def test_multi_form(self):        
        p = self.sess.find_element("Person:eddie")
        assert_not_equal(p, None, "could not find Person:eddie")
        eq_(p.age, 12)
        
        a = self.sess.find_element("Address:ADDR-eddie-Work")
        eq_(a.person, p)


    def test_update_resource(self):
        proc = MultiElementFormProcessor(self.sess)
        
        form = self.read_form("update_resource")      
        self.sess.begin() 
        proc.process(form)
        self.sess.commit()
        
        p = self.sess.find_element("Person:eddie")
        assert_not_equal(p, None, "could not find Person:eddie")
        
        

    def test_dump_form(self):        
        proc = MultiElementFormProcessor(self.sess, show_read_only=False, allow_create=True) 

        p = self.sess.find_element("Person:eddie")        
        
        actual_form = proc.to_form(p)
        
        expected_form = self.read_form("dump")
       
        self.compare_data(expected_form, actual_form)
 

