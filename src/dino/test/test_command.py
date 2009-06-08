import logging
import os
import sys

from nose.tools import *

from dino.db import *
from dino.test.base import * 
import dino.cmd

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint


###############################################
#
# UnitTest 
#

class ShowCommandTest(CommandTest, SingleSessionTest):
    
    def setUp(self):
        super(ShowCommandTest, self).setUp()
        self.sess.begin()
        
        for i in range(0,10):            
            o = Chassis(name="util-%d" % i, vendor="Grandma", product="")
            self.sess.add(o)   
                 
        self.sess.commit()

    def test_entity_name(self):
        value = self.runCommand('show', 'Chassis/')        
        eq_(len(value), 10)
        
    def test_element_name(self):
        value = self.runCommand('show', 'Chassis/util-3')   
        assert_true(isinstance(value, basestring), "output should be a string")
        
    def test_element_query(self):                
        value = self.runCommand('show', 'Chassis[vendor=Grandma]')
        eq_(len(value), 10)

    def test_attr_name1(self):
        value = self.runCommand('show', 'Chassis/util-3/vendor')        
        eq_(len(value), 1)  
        eq_(value[0], "Grandma")

    def test_attr_name2(self):
        value = self.runCommand('show', '-n', 'Chassis/util-3/vendor')        
        eq_(len(value), 1)  
        eq_(value[0], "Chassis/util-3/vendor Grandma")
    
    def test_attr_query(self):
        value = self.runCommand('show', 'Chassis[vendor=Grandma]/vendor')        
        eq_(len(value), 10)
        for x in value:  
            eq_(x, "Grandma")
        
    @raises(dino.cmd.CommandExecutionError)
    def test_bad_name(self):
        self.runCommand('show', 'OtherThing')


class GetSetCommandTest(CommandTest, ObjectTest, SingleSessionTest):
    def setUp(self):
        super(GetSetCommandTest, self).setUp()
        
        self.sess.begin()


        site1 = Site(name='old', address1="", address2="", city="", state="", postal="", description="") 
        self.sess.add(site1)

        site2 = Site(name="new", address1="", address2="", city="", state="", postal="", description="")
        self.sess.add(site2)

        rack = Rack(name="1.1A", site=site1)
        self.sess.add(rack)

        self.sess.commit()
        
        # Use the Object Id to reference this object
        # That will not change when the site changes        
        self.rack_name = rack.element_id
        self.site2_name = site2.element_name

    def test_get(self):        
        value = self.runCommand('get', '%s/name' % self.rack_name)
        eq_(type(value), list)
        eq_(value[0], "1.1A")
    
    def test_set_value(self):        
        self.runCommand('set', '%s/size' % self.rack_name, "200" )
        self.sess.expunge_all()
        o = self.sess.find_element(self.rack_name)        
        eq_( o.size, 200 )
    
    def test_set_object(self):        
        self.runCommand('set', '%s/site' % self.rack_name, self.site2_name )
        
        rack = self.sess.find_element(self.rack_name)        
        site2 = self.sess.find_element(self.site2_name)
                
        eq_(rack.site, site2)
    
    
class ShowRackTest(CommandTest, ObjectTest, SingleSessionTest, DataTest):
    DATA_DIR = "command"
    
    def setUp(self):
        super(ShowRackTest, self).setUp()
        
        r = self.create_rack(self.sess)    
            
        self.name = r.element_name
        
        self.sess.begin()
                        
        c1 = Chassis(name='small', vendor='yourmom', product='yourmom', racksize=1)        
        c2 = Chassis(name='medium', vendor='yourmom', product='yourmom', racksize=2)
        c3 = Chassis(name='large', vendor='yourmom', product='yourmom', racksize=4)
        
        for i in xrange(1,6,2):
            self.sess.add(Device(hid="XXX:%s" % i, rackpos=i, rack=r,  chassis=c1, serialno='1234-%d' % i))
        for i in xrange(9,18,3):
            self.sess.add(Device(hid="XXX:%s" % i, rackpos=i, rack=r,  chassis=c2, serialno='1234-%d' % i))
        for i in xrange(20,48,5):
            self.sess.add(Device(hid="XXX:%s" % i, rackpos=i, rack=r,  chassis=c3, serialno='1234-%d' % i))

        self.sess.commit()
    
        
    def test_showrack(self):
        actual_lines = self.runCommand('show', self.name)
        
        filename = self.get_datafile('showrack.output')
        f = open(filename)
        expected_lines = f.read().split("\n")
        f.close()
        
        self.compare_lines(expected_lines, actual_lines)
        
        
class AvailIpCommandTest(CommandTest, SingleSessionTest):
    def setUp(self):
        super(AvailIpCommandTest, self).setUp()
        
        self.sess.open_changeset()
        
        top = Subnet(addr="127.0.0.1/24")
        self.sess.add(top)
        bottom = Subnet(addr="127.0.0.1/25")
        
        bottom.parent = top
        self.sess.add(bottom)
        
        self.sess.add(Range(subnet=bottom, start=1, end=10, range_type='policy'))
        self.sess.add(Range(subnet=bottom, start=12, end=16, range_type='dhcp'))
        
        self.sess.submit_changeset()
        
    def test_next_ip(self):        
        ip_list = self.runCommand('ip', 'avail', 'Subnet/127.0.0.0_25', '2')
        
        assert ip_list is not None
        assert len(ip_list) == 2
        self.assertEquals(ip_list[0], "127.0.0.11")
        self.assertEquals(ip_list[1], "127.0.0.17")

    @raises(dino.cmd.CommandExecutionError)
    def test_fail_too_many(self): 
        self.runCommand('ip', 'avail', 'Subnet/127.0.0.0_25', '1000') 
        
    @raises(dino.cmd.CommandExecutionError)
    def test_fail_not_leaf(self):      
        self.runCommand('ip', 'avail', 'Subnet/127.0.0.0_24')

        
        
        
class SetIpCommandTest(CommandTest, ObjectTest, SingleSessionTest):
    
    def setUp(self):
        super(SetIpCommandTest, self).setUp()
        
        d = self.create_devices(self.sess)[0]
        self.create_hosts(self.sess)
            
        self.name1 = d.host.interfaces[0].element_name
        self.name2 = d.host.interfaces[1].element_name
        
        
        self.sess.begin()
        
        s = Subnet(addr="127.0.0.0", mask_len=24)
        r = Range(subnet=s, start=1, end=10, range_type='net')
        self.sess.add(s)
                
        self.sess.commit()
        
    def test_setip(self):
        #
        # Test IP gets set on the interface
        #        

        self.runCommand('ip', 'set', self.name1, '127.0.0.20')
        
        iface = self.sess.resolve_element_spec(self.name1)                      
        eq_( iface.address.value, "127.0.0.20" )


        #
        # Test setting the second Iface to same IP and fail 
        #
        assert_raises( dino.cmd.CommandExecutionError, 
            lambda: self.runCommand('ip', 'set', self.name2, '127.0.0.20') )

        try:
            self.runCommand('ip', 'set', self.name1, '127.0.0.1') 
        except dino.cmd.CommandExecutionError, e:
            assert_true( isinstance( e.__cause__, ResourceCreationError ), "Cause: %s" % e.__cause__) 
            
        #
        # Validate that Old IP gets deleted 
        #
        self.runCommand('ip', 'set', self.name1, '127.0.0.30')            
        addr = self.sess.query(IpAddress).filter_by(value='127.0.0.20').first()
        
        self.assertEquals(addr, None)
                
        

class ImportCommandTest(CommandTest, DataTest):
    DATA_DIR = "jsonimport"

    def setUp(self):
        super(ImportCommandTest, self).setUp()
        sess = self.db.session()
                
        sess.open_changeset()  

        sess.add(Appliance(name='mwdeploy', os=OperatingSystem(name='baccus')))    

        site = Site(name='sjc1', address1="", address2="", city="", state="", postal="", description="")
        rack = Rack(name="10", site=site)        
        sess.add(Subnet(addr="10.2.10.27", mask_len=24, site=site))

        chassis = Chassis(name='util', vendor='yourmom', product='yourmom')      
        netdev = Device(hid="1134345", serialno="1234", rack=rack, chassis=chassis, hw_class="network")
        nethost = Host(name="a10s1", pod=Pod(name='net'), device=netdev)
        sess.add(netdev)   
             
        sess.add(Pod(name='p01'))
        
        sess.submit_changeset()

        sess.close()
        
        
    def test_basic_import(self):    
        sess = self.db.session()
         
        path = self.get_datafile("host1.json")        
        
        self.runCommand('jsonimport', path)
        devices = sess.query(Device).filter_by(hw_class="server").all() # filter_by(hid="001EC943AF41")

        self.assertEqual(len(devices), 1)
        
        device = devices[0]
        
        self.assertEqual( device.hid, "001EC943AF41" )
        self.assertEqual( device.serialno,  "..CN7082184700NF.")
        self.assertEqual( device.rackpos,  13)
        self.assertNotEqual( device.host, None )

        sess.close()
    
    
    def test_update(self):
        sess = self.db.session()   
        
        path = self.get_datafile("host1.json")        
        self.runCommand('jsonimport', path)
        
        path = self.get_datafile("update1.json")        
        self.runCommand('jsonimport', path)
        
        devices = sess.query(Device).filter_by(hw_class="server").all()
        self.assertEqual(len(devices), 1)
        
        device = devices[0]
        
        self.assertEqual( device.hid, "001EC943AF41" )
        self.assertEqual( device.serialno,  "..CN7082184700NF")
        self.assertEqual( device.rackpos,  16)
        self.assertEqual( device.pdu_port,  '3')      
        


if __name__ == "__main__":
#    suite = unittest.TestSuite()
#    suite.addTest(ShowRackTest('test_showrack'))
#    suite.runTest()
    x = ShowRackTest()
    x.setUp()
    r = x.sess.find_element(x.name)
    for d in r.devices:
        print str(d)
    import pdb;pdb.set_trace()
        
        
        