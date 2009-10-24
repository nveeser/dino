import os, sys
from os.path import join, abspath, dirname
import logging
import unittest
from nose.tools import *


from dino.cli import LogController, DinoFileConfiguration
from dino.db.dbconfig import DbConfig
#from dino.db.schema import *
import dino.db.schema as meta
from dino.cmd import DinoCommand, CommandExecutionError

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint


class DinoTest(object):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        formatter = logging.Formatter('%(name)s: %(levelname)s: %(message)s')
        LogController().console_handler.setFormatter(formatter)
        self.log = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

    def tearDown(self):
        pass


class DataTest(DinoTest):
    DATA_DIR = None

    @classmethod
    def setUpClass(cls):
        super(DataTest, cls).setUpClass()

        if cls.DATA_DIR != None:
            cls.basedir = abspath(join(dirname(__file__), "data", cls.DATA_DIR))
        else:
            cls.basedir = abspath(join(dirname(__file__), "data"))

    @classmethod
    def get_datafile(cls, shortname):
        path = os.path.join(cls.basedir, shortname)
        assert os.path.exists(path), "Could not find file: %s" % path
        return path

    @classmethod
    def read_form(cls, formname):
        path = cls.get_datafile("%s.form" % formname)
        return open(path).read()

    def compare_data(self, expected, actual):
        expected_lines = expected.split('\n')
        actual_lines = actual.split('\n')

        self.compare_lines(expected_lines, actual_lines)

    def compare_lines(self, expected_lines, actual_lines):


        try:
            eq_(len(expected_lines), len(actual_lines))
            eq_(expected_lines, actual_lines)
        except:
            self._print_lines(expected_lines, actual_lines)
            raise

    def _print_lines(self, expected_lines, actual_lines):

        count = len(expected_lines) > len(actual_lines) and len(expected_lines) or len(actual_lines)

        for i in range(0, count):
            try:
                expected_line = expected_lines[i]
            except IndexError:
                expected_line = None

            try:
                actual_line = actual_lines[i]
            except IndexError:
                actual_line = None

            if expected_line != actual_line:
                print "--Differ: %d" % i
                print "Exp: [%s]" % expected_line
                print "Got: [%s]" % actual_line

        print "((((((((((((((((( EXPECTED )))))))))))))))))"
        print "\n".join(expected_lines)
        print "(((((((((((((((((  ACTUAL  )))))))))))))))))"
        print "\n".join(actual_lines)
        print "(((((((((((((((((   END    )))))))))))))))))"



class DatabaseTest(DinoTest):
    ENTITY_SET = None
    CONFIG_SECTION = 'unittest.db'

    def setUp(self):
        super(DatabaseTest, self).setUp()
        self.db.create_all()


    def tearDown(self):
        super(DatabaseTest, self).tearDown()
        #self.db.clear_schema()


    @classmethod
    def setUpClass(cls):
        super(DatabaseTest, cls).setUpClass()
        cls.db = cls.get_database_config(cls.ENTITY_SET)
        cls.db.create_all()


    @classmethod
    def tearDownClass(cls):
        super(DatabaseTest, cls).tearDownClass()
        cls.db.drop_all()

    @classmethod
    def get_database_config(cls, entity_set):
        opts = {
        'user' : None,
        'password' : None,
        'host' : None,
        'db' : None,
        'url' : None,
        'entity_set' : entity_set,
        }


        file_config = DinoFileConfiguration()
        for n, v in file_config[cls.CONFIG_SECTION].iteritems():
            opts[n] = v

        return DbConfig(**opts)


class DatabaseResetTest(DatabaseTest):
    ''' 
    Adds fixtures to reset the database after each test.
    '''
    def setUp(self):
        self.setUpClass()
        super(DatabaseResetTest, self).setUp()


    def tearDown(self):
        self.tearDownClass()
        super(DatabaseResetTest, self).tearDown()

class SingleSessionTest(DatabaseTest):

    def setUp(self):
        super(SingleSessionTest, self).setUp()
        self.sess = self.db.session()


    def tearDown(self):
        super(SingleSessionTest, self).tearDown()
        self.sess.close()


    def load_form(self, formdata):
        proc = MultiCreateFormProcessor(self.sess)
        self.sess.begin()
        proc.process(formdata)
        self.sess.commit()


#class DoubleSessionTest(DatabaseTest):
#    '''currently unused'''    
#    def setUp(self):
#        super(DoubleSessionTest, self).setUp()
#        self.sess1 = self.db.session()
#        self.sess2 = self.db.session()
#                
#    def tearDown(self):
#        super(SingleSessionTest, self).tearDown()
#        self.sess1.close()
#        self.sess2.close()


class ObjectTest(DatabaseTest):
    ENTITY_SET = meta.entity_set

    def setUp(self):
        super(ObjectTest, self).setUp()

        self.objects = {}

    def create_rack(self, session):
        session.begin()

        s = Site(name='sjc1', address1="", address2="", city="", state="", postal="", description="")
        r = Rack(name="1.1", site=s)

        session.add(r)
        self.objects['rack'] = r
        self.log.info("Created: %s", r)

        session.commit()

        return self.objects['rack']

    def create_devices(self, session, count=1):

        if 'rack' not in self.objects:
            r = self.create_rack(session)
        else:
            r = self.objects['rack']

        session.begin()

        c1 = Chassis(name='small', vendor='yourmom', product='yourmom', racksize=1)

        self.objects['devices'] = []
        for i in range(0, count, 4):
            d = Device(hid="XXX:%s" % i, rackpos=i, rack=r, chassis=c1, serialno='1234-%02x' % i)
            d.ports.append(Port(name="eth0", mac="03:03:03:03:%02x:01" % i))
            d.ports.append(Port(name="eth1", mac="03:03:03:03:%02x:02" % i))

            session.add(d)
            self.objects['devices'].append(d)

            self.log.info("Created: %s", d)

        session.commit()

        return self.objects['devices']

    def create_hosts(self, session, count=1):

        if not 'devices' in self.objects:
            self.create_devices(count)

        session.begin()

        pod = Pod(name='pod01')

        for d in self.objects['devices']:
            d.host = Host(name="host-%s" % d.id, pod=pod)

            self.log.fine("Created: %s", d.host)
            for port in d.ports:
                d.host.interfaces.append(Interface(port_name=port.name))
                self.log.fine("Created: Interface/%s", port.name)

        # no need to add, it was assigned to device
        session.commit()

        return [ d.host for d in self.objects['devices'] ]










