import os
import sys

from nose.tools import *

from dino.test.base import *
from dino.test.simplemodel import *
from dino.db import ElementPropertyError, UnknownElementError

class TestSetElementProperty(SingleSessionTest):
    ENTITY_SET = simple_entity_set


class TestSetElementPropertyColumn(TestSetElementProperty):

    @classmethod
    def setUpClass(cls):
        super(TestSetElementProperty, cls).setUpClass()

        sess = cls.db.session()
        person = Person(name='eddie', age=12)
        sess.begin()
        sess.add(person)
        sess.commit()

    def test_set_good(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('age')
        element_property.set("12")
        eq_(person.age, 12)

    def test_set_none(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('age')
        element_property.set("None")
        eq_(person.age, None)

    def test_set_none2(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('age')
        element_property.set(None)
        eq_(person.age, "")

    @raises(ElementPropertyError)
    def test_set_bad_input(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('age')
        element_property.set("BadInput")
        eq_(person.age, None)



class TestSetElementPropertyToOne(TestSetElementProperty):
    @classmethod
    def setUpClass(cls):
        super(TestSetElementProperty, cls).setUpClass()

        sess = cls.db.session()
        sess.begin()

        person = Person(name='eddie', age=12)
        sess.add(person)
        sess.add(PhoneNumber(number="123123", person=person))
        sess.add(Company(name="kidco", value1=12))
        sess.commit()

    def test_set_element(self):
        person = self.sess.find_element("Person:eddie")

        element_property = person.element_property('phone_number')
        number = PhoneNumber(number="555555")
        element_property.set(number)


    def test_set_element_spec(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('company')
        element_property.set("Company:kidco")

        company = self.sess.find_element("Company:kidco")
        eq_(person.company, company)

    @raises(UnknownElementError)
    def test_set_element_spec_fail(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('company')
        element_property.set("Company:non-existant")

    def test_set_resource_element(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('phone_number')
        element_property.set("123-123")

        eq_(person.phone_number.number, "123-123")

class TestSetElementPropertyToMany(TestSetElementProperty):

    @classmethod
    def setUpClass(cls):
        super(TestSetElementPropertyToMany, cls).setUpClass()

        sess = cls.db.session()
        sess.begin()

        person = Person(name='eddie', age=12)
        sess.add(person)

        for i in xrange(1, 5):
            sess.add(Address(person=person, value1="work%d" % i))

        sess.commit()

    def test_add_relation(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('addresses')
        addr = Address(value1="Room 500")

        element_property.add(addr)
        eq_(len(person.addresses), 5)


    @raises(ElementPropertyError)
    def test_add_fail(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('addresses')
        addr = Address(value1="work", value2=1232)

        element_property.add(addr)
        eq_(len(person.addresses), 5)

        element_property.add(addr)
        eq_(len(person.addresses), 5)

    def test_remove(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('addresses')
        element_property.remove("Address:ADDR-eddie-work3")

        eq_(len(person.addresses), 3)


    @raises(UnknownElementError)
    def test_remove_fail(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('addresses')
        element_property.remove("Address:ADDR-eddie-work10")


    def test_set(self):
        person = self.sess.find_element("Person:eddie")
        element_property = person.element_property('addresses')
        element_property.set([ 'Address:ADDR-eddie-work2', 'Address:ADDR-eddie-work3' ])

        eq_(len(person.addresses), 2)
