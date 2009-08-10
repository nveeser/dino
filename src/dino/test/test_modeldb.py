#!/usr/bin/env python

import os,sys

if __name__ == "__main__":
    sys.path[0] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from nose.tools import *

from dino.db import *
from dino.test.base import *



###############################################
#
# UnitTest 
#

class TestSubnet(DatabaseTest):
    
    def test_add_subnet(self):
        sess = self.db.session() 
        
        sess.open_changeset()
        subnet = Subnet(addr="127.0.0.1/24")        
        sess.add(subnet)
        sess.submit_changeset()
        
        subnets = sess.query(Subnet).all()
        
        eq_( len(subnets), 1 )
        
        eq_(subnets[0].addr, "127.0.0.0")
        eq_(subnets[0].mask, "255.255.255.0")
        
    

        
        

    