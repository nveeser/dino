
import os
import sys

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    
from nose.tools import *

from dino.test.base import *
from dino.test.simplemodel import *


class TestElement(DinoTest):
    
    @raises(RuntimeError)
    def test_invalid_attr(self):    
        Person(foo="123")
            
        
    def test_regex(self):
        def value_test(entity, spec, full_result, entity_result, instance_result):  
            m = entity.element_name_regex().match(spec)        
            eq_( m.group(1), full_result)
            eq_( m.group(2), entity_result)
            eq_( m.group(3), instance_result)


        arg_list = (
            (Person, "Person:foo", "Person:foo", "Person", "foo"),
            (Person, "Person:{1}", "Person:{1}", "Person", "{1}"),
            (Person, "Person:<1>", "Person:<1>", "Person", "<1>"),
        )
            
    
        for args in arg_list:
            yield (value_test, ) + args
        

class TestPerson(DatabaseTest):
    ENTITY_SET = simple_entity_set    
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
    ENTITY_SET = simple_entity_set        
    PERSON = 'eddie'
    ADDRESS = "Home"
    ADDRESS_INSTANCE_NAME = "ADDR-eddie-Home"

    @classmethod
    def setUpClass(cls):
        super(TestAddress, cls).setUpClass()
        
        sess = cls.db.session()
        sess.begin()
        p = Person(name=cls.PERSON, age=12)         
        a = Address(value1=cls.ADDRESS, value2=12, person=p)    
        sess.add(p)                        
        sess.commit()
        
        
    def test_address_query(self):
        sess = self.db.session() 

        p = sess.query(Person).filter_by(instance_name=self.PERSON).first()

        a = sess.query(Address).filter_by(instance_name=self.ADDRESS_INSTANCE_NAME).first()
        eq_(a.value1, self.ADDRESS)

        p.name = self.PERSON + "ex"                
        eq_('ADDR-eddieex-Home', a.instance_name )

        