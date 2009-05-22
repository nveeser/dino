#!/usr/bin/env python

from dino.db import * 
import unittest


import pprint
pp = pprint.PrettyPrinter(indent=2).pprint




class AddressMathTest(unittest.TestCase):
    
    ntoa_pairs = { 0x0A0A0A0A : "10.10.10.10", 
                   0xFFFFFFFF : "255.255.255.255", }
                   
                    
    def test_all_ntoa(self):
        for n,a in AddressMathTest.ntoa_pairs.items():
            result = IpType.ntoa(n)        
            self.assertEqual( result, a )
            
            result = IpType.aton(a)
            self.assertEqual( result, n )
            

    mask_pairs = {  32 : "255.255.255.255",
                    24  : "255.255.255.0",
                    16 : "255.255.0.0",
                    8 : "255.0.0.0",
                    0 : "0.0.0.0", }
                    

    def test_mask(self):
        for l, a in AddressMathTest.mask_pairs.items():
            n = IpType.aton(a)
            
            result = Subnet.len_to_mask(l)
            self.assertEqual( result, n )
            
            result = Subnet.mask_to_len(n)
            self.assertEqual( result, l )
            
    init_pairs = [  
        ("127.0.0.1/24", "127.0.0.0"),
        ("127.0.0.20/24", "127.0.0.0"), 
    ]
            
    def test_init(self):
        for net_spec, net_name in self.init_pairs:            
            s = Subnet(addr=net_spec)
            self.assertEqual( s.addr, net_name )
        
        
    broadcast_pairs = [
        ("127.0.0.1/24", "127.0.0.255"),
        ("127.0.0.0/30", "127.0.0.3"),
        ("127.0.0.3/28", "127.0.0.15"), 
    ]
        
    def test_broadcast(self):
        for net_spec, bcast in self.broadcast_pairs:
            s = Subnet(addr=net_spec)
            nbcast = IpType.aton(bcast)
            #print IpType.ntoa( s.broadcast ), bcast
            self.assertEquals( s.broadcast, nbcast )
        
        
        
class AddressSetTest(unittest.TestCase):
    
    test_subnet_pairs = [ 
        ("10.0.0.1/24", 254),
        ("10.0.0.1/25", 126),
        ("10.0.0.1/26", 62), 
    ]
        
    def test_subnet_set(self):
        for net, count in self.test_subnet_pairs:   
            s = Subnet(addr=net)        
            ip_set = s.naddr_set()
 
            self.assertEqual( len(ip_set), count)
        
    def test_range_set(self):
        for net, count in self.test_subnet_pairs:            
            subnet = Subnet(addr=net)                
            r = Range(subnet=subnet, start=1, end=10, range_type='policy')
            set = r.naddr_set()

            self.assertEquals( len(set), 10 )
            
            
            


