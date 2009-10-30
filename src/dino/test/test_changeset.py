import os, sys
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

from simplemodel import *

###############################################
#
# UnitTest 
#
###############################################


class ChangeSetTest(SingleSessionTest):
    ENTITY_SET = simple_entity_set

    def setUp(self):
        super(ChangeSetTest, self).setUp()
        self.db.create_all()

        session = self.db.session()

        session.open_changeset()
        p = Person(name='eddie', age=12)
        session.add(p)
        session.submit_changeset()

        assert session.last_changeset is not None


    def tearDown(self):
        super(ChangeSetTest, self).tearDown()
        self.db.clear_schema()



class TestChangeSet(ChangeSetTest):

    def test_add_person(self):

        for stmt in ["SELECT * FROM person", "SELECT * FROM person_revision"]:
            result = self.sess.execute(stmt)

            rows = result.fetchall()
            assert len(rows) == 1
            myrow = rows[0]

            eq_(myrow['name'], 'eddie')
            eq_(myrow['age'], 12)


    def test_add_address(self):
        self.sess.open_changeset()

        p = self.sess.query(Person).filter_by(name='eddie').first()
        a = Address(value1='Home', value2=12, person=p)
        self.sess.add(a)

        self.sess.submit_changeset()


    def test_delete_person(self):
        p = self.sess.query(Person).filter_by(name='eddie').first()
        self.sess.open_changeset()
        self.sess.delete(p)
        print "DELETE SUBMIT"
        cs = self.sess.submit_changeset()

        assert self.sess.last_changeset is not None
        assert cs is not None

        result = self.sess.query(Person).filter_by(name='eddie').all()

        assert len(result) == 0


class TestRevision(ChangeSetTest):

    def setUp(self):
        super(TestRevision, self).setUp()

        p = self.sess.query(Person).filter_by(name='eddie').first()
        for i in xrange(4):
            self.sess.open_changeset()
            p.age += 1
            self.sess.submit_changeset()

        self.sess.expunge_all()


    def test_revision(self):

        p = self.sess.query(Person).filter_by(name='eddie').first()

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
        a = Address("12.12.12.%d" % (i + 100), i)
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
    db = get_database_config(entity_set)

    #print db.dump_schema()
    do_insert(db)
    #do_updates(db)
    #do_delete(db)
    #do_revisions(db)

