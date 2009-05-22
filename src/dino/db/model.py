
from sqlalchemy.orm import ColumnProperty, validates, object_session
from sqlalchemy import func, types
from sqlalchemy.databases.mysql import MSInteger

import schema
from dino.db.exception import *

# # # # # # # # # # # # # # # # # # # 
#  Special Types
# # # # # # # # # # # # # # # # # # # 

class IpType(types.TypeDecorator):
    # Prefixes Unicode values with "PREFIX:" on the way in and
    # strips it off on the way out.
    impl = MSInteger
    
    def __init__(self):
        self.impl = MSInteger(unsigned=True)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, basestring):
            raise ValueError("IpType must be assigned as an string, not %s" % type(value))
        return self.aton(value)

    def process_result_value(self, value, dialect):
        return self.ntoa(value)
        
    @staticmethod
    def aton(ip):
        assert isinstance(ip, basestring)
        try:
            hexn = ''.join(['%02X' % long(i) for i in ip.split('.')])
            return long(hexn, 16)
        except ValueError, ex:
            raise InvalidIpAddressError(ip)
    
    @staticmethod
    def ntoa(n):
        return '%d.%d.%d.%d' % ((n>>24) & 0xff, (n>>16) & 0xff, (n>>8) & 0xff, n & 0xff)    


class StringSetType(types.TypeDecorator):
    def __init__(self, length, choices):
        self.impl = types.String(length)
        self.choices = set([ c.lower() for c in choices ]) 
        
    def process_bind_param(self, value, dialect):

        return value

    def process_result_value(self, value, dialect):
        return value
        
        
    class Ipv4Quad(object):
        MASK = 0xFFFFFFFF        
        def __init__(self, value):
            if isinstance(value, int):
                self.naddr = value
            elif isinstance(value, str):
                self.naddr = IpType.aton(value)
                
        def __eq__(self, other):
            assert isinstance(other, Ipv4Quad)            
            return self.naddr == other.naddr
            
        def __and__(self, other): 
            assert isinstance(other, Ipv4Quad)            
            return (self.naddr & other.naddr) & self.MASK
        
        def __xor__(self, other): 
            assert isinstance(other, Ipv4Quad)
            return (self.naddr ^ other.naddr) & self.MASK
            
        def __or__(self): 
            assert isinstance(other, Ipv4Quad)
            return (self.naddr ^ other.naddr) & self.MASK
            
        def __invert__(self): 
            return ~self.naddr & self.MASK
            
        def __str__(self):
            return IpType.ntoa(self.naddr)
        
            

# # # # # # # # # # # # # # # # # # # 
#  Validators
# # # # # # # # # # # # # # # # # # # 

class Device(object):
    @validates('status', 'rackpos')
    def validate(self, name, value):
        if name == "status":
            if value.upper() not in [ 'INVENTORY','ACTIVE', 'BROKEN', 'DEAD', 'RMA' ]:
                raise ValueError("Value must be one of %s" % self.choices)
                
#        if name == 'rackpos':
#            if self.rack is not None and self.rackpos is None:
#                raise ValueError(" A device in a Rack must have a RackPos")
                
        return value
    
    
class IpAddress(object):

    #
    # Properties
    # 
    def _get_nvalue(self):
        return IpType.aton(self.value)
        
    def _set_nvalue(self, naddr):
        self.value = IpType.ntoa(naddr)
        
    nvalue = property(_get_nvalue, _set_nvalue)
    
    @property
    def nsubnet(self):
        if self._subnet is None:
            
            session = object_session(self)
            assert session is not None, "Object must have session to perform query"
            
            sql_netmask = func.power(2,32) - func.power(2, (32-schema.Subnet.mask_len))
            
            self._subnet = session.query(Subnet)\
                    .filter( schema.Subnet.addr == sql_netmask.op('&')(self.nvalue) )\
                    .order_by( schema.Subnet.mask_len.desc() )\
                    .first()
    
        return self._subnet
    #
    # Methods
    #   
    def __int__(self):
        return self.nvalue
  
      
    def query_subnet(self):
        session = object_session(self)
        assert session is not None, "Object must have session to perform query"
        
        sql_netmask = func.power(2,32) - func.power(2, (32-schema.Subnet.mask_len))
        
        q = session.query(schema.Subnet)\
                .filter( schema.Subnet.addr == sql_netmask.op('&')(self.nvalue) )\
                .order_by( schema.Subnet.mask_len.desc() )
                
        return q.first()
  
    @staticmethod
    def int2bin(n, count=32):
        """returns a string repr of the int in binary"""
        return "".join([str((n >> y) & 1) for y in range(count-1, -1, -1)])
   
    
class Subnet(object):
    
    @validates('mask_len')    
    def validate_mask_len(self, name, value):
        if value is not None:
            value = int(value)
            assert value >= 0 and value <= 32        
        return value

    @staticmethod
    def len_to_mask(n):
        mask = 0
        for i in range(32-n,32):
            mask += 1L<<i
        return mask        
        
    @staticmethod
    def mask_to_len(n):
        len = 0        
        for i in range(31,-1,-1):
            if n >> i & 1: len +=1
            else: break 
        return len

    #
    # Properties
    #     
    def _get_nmask(self):
        return Subnet.len_to_mask(self.mask_len)        
    def _set_nmask(self, mask):
        self.mask_len = Subnet.mask_to_len(mask)
        
    nmask = property(_get_nmask, _set_nmask)

    def _get_mask(self):
        return IpType.ntoa(self._get_nmask())
    def _set_mask(self, mask):
        nmask = IpType.aton(mask)
        self._set_nmask(nmask)
        
    mask = property(_get_mask, _set_mask)

    def _get_naddr(self):
        return IpType.aton(self.addr)        
    def _set_naddr(self, naddr):        
        self.addr = IpType.ntoa(naddr)

    naddr = property(_get_naddr, _set_naddr)
    
    @property
    def broadcast(self):
        return (self.naddr + (~self.nmask & 0xFFFFFFFF)) 
        
    #
    # Methods
    #   
    def contains(self, address):      
        if isinstance(address, schema.IpAddress):
            return self.naddr == self.nmask & address.naddr
        elif isinstance(address, (int,long)):
            return self.naddr == self.nmask & address
        elif isinstance(address, basestring):
            return self.naddr == self.nmask & IpType.aton(address)
        else:
            raise ValueError("method contains takes { IpAddress | int | str }, not %s" % type(address))

    
    def naddr_set(self):
        """ return a set of integers representing IP addresses """
                
        first = (self.naddr & self.nmask) + 1        
        last = self.broadcast
        return set( range(first, last) )

    def size(self):
        first = (self.naddr & self.nmask) + 1        
        last = self.broadcast        
        return last - first + 1
        
        
    def avail_ip_set(self):
        if len(self.children) > 0:
            raise ModelError("Cannot get available IP set from Non-Leaf subnet")
        
        ip_set = self.naddr_set()
                
        for r in self.ranges:
            ip_set -= r.naddr_set()
                    
        for ip in self.addresses:
            ip_set -= ip.naddr

        return ip_set
        
class Range(object):
    TYPES = ('dhcp', 'policy')
    
    @validates('type')
    def validate_type(self, name, value):
        if name == 'type' and value not in self.TYPES:
            raise ModelError("Invalid type. Must be %s not: %s" % (self.TYPES, value))
    
    @validates('start', 'end')
    def validate_size(self, name, value):
        if not self.subnet:
            return value
            
        naddr = self.subnet.naddr + value
        if not self.subnet.contains(naddr):
             raise ModelError("%s is not within subnet: %s" % (name, value))
                 
        return value
    
        
    def _get_start_addr(self):
        return IpType.ntoa(self.start_naddr)
    
    def _set_start_addr(self, value):
        if not isinstance(value, basestring):
            raise ValueError("start_addr must be assigned a basestring: %s" % type(value))
        self.start_naddr = IpType.aton(value)
                
    def _get_end_addr(self):
        return IpType.ntoa(self.end_naddr)
        
    def _set_end_addr(self, value):
        if not isinstance(value, basestring):
            raise ValueError("start_addr must be assigned a basestring: %s" % type(value))
        self.end_naddr = IpType.aton(value)
        
    start_addr = property(_get_start_addr, _set_start_addr)
    end_addr = property(_get_end_addr, _set_end_addr)
            
    def _get_start_naddr(self):
        return self.subnet.naddr + self.start
    
    def _set_start_naddr(self, value):
        if not isinstance(value, (int, long)):
            raise ValueError("Must supply an int")
        
        if not subnet.contains(value):
            raise ValueError("Address not within subnet: %s" % IpType.ntoa(value))
            
        self.start = value - self.subnet.naddr
         
            
    def _get_end_naddr(self):
        return self.subnet.naddr + self.end
    
    def _set_end_naddr(self, value):
        if not isinstance(value, (int, long)):
            raise ValueError("Must supply an int")
        
        if not subnet.contains(value):
            raise ValueError("Address not within subnet: %s" % IpType.ntoa(value))
            
        self.end = value - self.subnet.naddr 
        
    start_naddr = property(_get_start_naddr, _set_start_naddr)
    end_naddr = property(_get_end_naddr, _set_end_naddr)
    

    def naddr_set(self):
        start = self.subnet.naddr + self.start
        end = self.subnet.naddr + self.end + 1
        return set( range(start, end) )
        
    def size(self):
        start = self.subnet.naddr + self.start
        end = self.subnet.naddr + self.end + 1
        return end - start + 1
        
    def contains(self, arg):
        naddr_set = self.naddr_set()        
        
        if isinstance(arg, int):
            return arg in naddr_set
        elif isinstance(arg, basestring):
            return IpType.aton(arg) in naddr_set
        elif isinstance(arg, schema.IpAddress):
            return arg.nvalue in naddr_set
        else:
            raise ModelArgumentError("Argument to contains must be a str or int")

        
        
        
        
        
        
        
        