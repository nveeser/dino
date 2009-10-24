import logging
import os
import sys

from nose.tools import *

if __name__ == "__main__":
    sys.path[0] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from dino.db import *
from dino.test.base import *
import dino.cmd
from dino.cli import BaseCommandEnvironment

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint


###############################################
#
# UnitTest 
#

class TestCommandContext(BaseCommandEnvironment):
    def __init__(self):
        BaseCommandEnvironment.__init__(self)
        self.output = []

    def setup_base_logger(self, logger_name=""):
        pass

    def write(self, line):
        self.output.append(line)


class CommandTest(DatabaseTest):
    DATA_DIR = "command"

    def runCommand(self, *args):
        (cmdname, args) = (args[0], list(args[1:]))
        cmd_cls = DinoCommand.find_command(cmdname)
        cmd = cmd_cls(self.db, TestCommandContext())
        cmd.parse(args)
        cmd.execute()
        return cmd.cmd_env.output


class TestShowCommand(CommandTest, SingleSessionTest):

    @classmethod
    def setUpClass(cls):
        super(TestShowCommand, cls).setUpClass()

        sess = cls.db.session()

        sess.begin()
        for i in range(0, 10):
            o = Chassis(name="util-%d" % i, vendor="Grandma", product="")
            sess.add(o)

        sess.commit()

    def test_entity_name(self):
        value = self.runCommand('show', 'Chassis:')
        eq_(len(value), 10)

    def test_element_name(self):
        value = self.runCommand('show', 'Chassis:util-3')
        eq_(len(value), 1)

        assert_true(isinstance(value[0], basestring), "output should be a string")

    def test_element_query(self):
        value = self.runCommand('show', 'Chassis[vendor=Grandma]')
        eq_(len(value), 10)

    def test_attr_name1(self):
        value = self.runCommand('show', 'Chassis:util-3/vendor')
        eq_(len(value), 1)
        eq_(value[0], "Grandma")

    def test_attr_name2(self):
        value = self.runCommand('show', '-n', 'Chassis:util-3/vendor')
        eq_(len(value), 1)
        eq_(value[0], "Chassis:util-3/vendor Grandma")

    def test_attr_query(self):
        value = self.runCommand('show', 'Chassis[vendor=Grandma]/vendor')
        eq_(len(value), 10)
        for x in value:
            eq_(x, "Grandma")

    @raises(dino.cmd.CommandExecutionError)
    def test_bad_name(self):
        self.runCommand('show', 'OtherThing')



class TestShowRack(CommandTest, SingleSessionTest, DataTest):
    DATA_DIR = "command"

    @classmethod
    def setUpClass(cls):
        super(TestShowRack, cls).setUpClass()
        sess = cls.db.session()

        sess.begin()
        proc = MultiElementFormProcessor(sess, allow_create=True)
        form = cls.read_form("rack")
        proc.process(form)
        form = cls.read_form("devices")
        proc.process(form)
        sess.commit()

        sess.close()

    def test_showrack(self):
        actual_data = self.runCommand('show', "Rack:sjc1.1.1")

        filename = self.get_datafile('showrack.output')
        f = open(filename)
        expected_data = f.read()
        f.close()

        self.compare_data(expected_data, actual_data[0])




class TestSetCommand(CommandTest, SingleSessionTest, DataTest):

    @classmethod
    def setUpClass(cls):
        super(TestSetCommand, cls).setUpClass()
        sess = cls.db.session()

        sess.begin()
        proc = MultiElementFormProcessor(sess, allow_create=True)
        form = cls.read_form("set_test_sites")
        proc.process(form)
        sess.commit()

        rack = sess.find_element("Rack:old.1.1A")
        cls.rack_id = rack.element_id

        sess.close()

    def test_set_value(self):
        self.runCommand('set', '%s/size' % self.rack_id, "200")
        self.sess.expunge_all()
        o = self.sess.find_element(self.rack_id)
        eq_(o.size, 200)

    def test_set_object(self):
        self.runCommand('set', '%s/site' % self.rack_id, "Site:new")

        rack = self.sess.find_element(self.rack_id)
        site2 = self.sess.find_element("Site:new")

        eq_(rack.site, site2)




class TestImportCommand(CommandTest, DataTest):
    DATA_DIR = "jsonimport"

    @classmethod
    def setUpClass(cls):
        super(TestImportCommand, cls).setUpClass()
        sess = cls.db.session()

        sess.begin()
        proc = MultiElementFormProcessor(sess, allow_create=True)
        form = cls.read_form("import_test")
        proc.process(form)
        sess.commit()

        sess.close()


    def test_basic_import(self):
        sess = self.db.session()

        path = self.get_datafile("host1.json")

        self.runCommand('jsonimport', path)
        devices = sess.query(Device).filter_by(hw_class="server").all() # filter_by(hid="001EC943AF41")

        eq_(len(devices), 1)

        device = devices[0]

        eq_(device.hid, "001EC943AF41")
        eq_(device.serialno, "..CN7082184700NF.")
        eq_(device.rackpos, 13)
        assert_not_equal(device.host, None)

        sess.close()


    def test_update(self):
        sess = self.db.session()

        path = self.get_datafile("host1.json")
        self.runCommand('jsonimport', path)

        path = self.get_datafile("update1.json")
        self.runCommand('jsonimport', path)

        devices = sess.query(Device).filter_by(hw_class="server").all()
        eq_(len(devices), 1)

        device = devices[0]

        eq_(device.hid, "001EC943AF41")
        eq_(device.serialno, "..CN7082184700NF")
        eq_(device.rackpos, 16)
        eq_(device.pdu_port, '3')



if __name__ == "__main__":
#    suite = unittest.TestSuite()
#    suite.addTest(ShowRackTest('test_showrack'))
#    suite.runTest()

    s = Site(name='sjc1', address1="", address2="", city="", state="", postal="", description="")
    r = Rack(name="1.1", site=s)

    c1 = Chassis(name='small', vendor='yourmom', product='yourmom', racksize=1)
    c2 = Chassis(name='medium', vendor='yourmom', product='yourmom', racksize=2)
    c3 = Chassis(name='large', vendor='yourmom', product='yourmom', racksize=4)

    def rack():
        return ("data/command/rack.form", s, r, c1, c2, c3)

    def devices():
        yield "data/command/devices.form"
        for i in xrange(1, 6, 2):
            yield Device(hid="XXX:%s" % i, rackpos=i, rack=r, chassis=c1, serialno='1234-%d' % i)
        for i in xrange(9, 18, 3):
            yield Device(hid="XXX:%s" % i, rackpos=i, rack=r, chassis=c2, serialno='1234-%d' % i)
        for i in xrange(20, 48, 5):
            yield Device(hid="XXX:%s" % i, rackpos=i, rack=r, chassis=c3, serialno='1234-%d' % i)


    def set_test():
        site1 = Site(name='old', address1="", address2="", city="", state="", postal="", description="")
        site2 = Site(name="new", address1="", address2="", city="", state="", postal="", description="")
        rack = Rack(name="1.1A", site=site1)
        return ("data/command/set_test_sites.form", site1, site2, rack)


    def import_test():

        os = OperatingSystem(name='baccus')
        appliance = Appliance(name='mwdeploy', os=os)

        site = Site(name='sjc1', address1="", address2="", city="", state="", postal="", description="")
        pod1 = Pod(name='p01')
        pod2 = Pod(name='net')

        rack = Rack(name="10", site=site)
        chassis = Chassis(name='util', vendor='yourmom', product='yourmom')
        netdev = Device(hid="1134345", serialno="1234", rack=rack, chassis=chassis, hw_class="network")
        nethost = Host(name="a10s1", pod=pod2, device=netdev)

        subnet = Subnet(addr="10.2.10.27", mask_len=24, site=site)

        return ("data/jsonimport/import_test.form", os, appliance, site, pod1, pod2, rack, chassis, netdev, nethost, subnet)


    proc = MultiElementFormProcessor(None, show_headers=False, show_read_only=False, allow_create=True)


    for func in rack, devices, set_test, import_test:
        x = list(func())
        file, objects = x[0], x[1:]
        print "Write: %s" % file

        f = open(file, 'w')
        f.write(proc.to_form(objects))
        f.close()

