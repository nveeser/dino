
''' 
Set of classes to parse and modify tinydns data files
'''

class MetaDnsRecord(type):
    def __init__(cls, name, bases, dict_):
        super(MetaDnsRecord, cls).__init__(name, bases, dict_)
        
        if bases[0] == list:
            cls.REC_TYPES = {}

        if not hasattr(cls,'FORMAT'):
            raise RuntimeError("subclasses must define FORMAT: %s" % name)
            
        if cls.FORMAT is None:
            return
        
        cls.KEY = cls.FORMAT[0]
        attrs = cls.FORMAT[1:].split(":")
        
        #print "%s: %s" % (name, cls.KEY)
        cls.REC_TYPES[cls.KEY] = cls
            
        for i, attr_name in enumerate(attrs):
            #print "%s.%s (%s)" % (name, attr_name, i)
            setattr(cls, attr_name, MetaDnsRecord.index_property(i))
        
    @staticmethod
    def index_property(index):
        
        def _get(self, index=index):
            if index < len(self):
                return self[index]
            else:
                return None
            
        def _set(self, value, index=index):
            for i in xrange(len(self), index+1):
                self.append("")
            self[index] = str(value)
            
        return property(_get, _set)    


class DnsRecord(list):
    __metaclass__ = MetaDnsRecord
    
    FORMAT = None
    
    def __init__(self, values=(), *args, **kwargs):
        list.__init__(self, values)
        
    def __str__(self):
        return "%s%s" % (self.KEY, ":".join(self))

    def __hash__(self):
       return hash(tuple(self.KEY) + tuple(self))

    def __lt__(self, other):
        if isinstance(other, DnsRecord):
            return str.__lt__(str(self), str(other))            
        else:   
            return NotImplemented
            
    def __eq__(self, other):
        return self.__class__ == other.__class__ and str(self) == str(other)
            
    def __ne__(self, other):
        return NotImplemented
            
    def __gt__(self, other):
        return NotImplemented
            
    def __ge__(self, other):
        return NotImplemented
            
    def __le__(self, other):
        return NotImplemented
    
    
    @staticmethod
    def parse_data_file(file):        
        f = open(file)
        try:
            # read lines, remove comments 
            lines = [ line.split("#", 1)[0].strip() for line in f.readlines() ]            
            # parse non-empty lines
            return [ DnsRecord.parse_record(line) for line in lines if line != "" ]
                
        finally:
            f.close()
    
    @classmethod
    def parse_record(cls, record):
        
        key = record[0]
        values = record[1:].split(":")
        
        if key not in cls.REC_TYPES.keys():
            raise Exception("Unknown Record Type: %s" % key)        
        else:
            return cls.REC_TYPES[key](values=values)
    

    
class FullSoaRecord(DnsRecord):
    FORMAT = ".fqdn:ip:x:ttl:timestamp:lo"
    '''
    * an NS (``name server'') record showing x.ns.fqdn as a name server for fqdn;
    * an A (``address'') record showing ip as the IP address of x.ns.fqdn; and
    * an SOA (``start of authority'') record for fqdn listing x.ns.fqdn as the primary name server and hostmaster@fqdn as the contact address. 
    '''    
    
    KEY = '.'

class NsOnlyRecord(DnsRecord):
    FORMAT = "&fqdn:ip:x:ttl:timestamp:lo"
    '''    
    * an NS record showing x.ns.fqdn as a name server for fqdn and
    * an A record showing ip as the IP address of x.ns.fqdn.     
    '''
    
class FullARecord(DnsRecord):
    FORMAT = "=fqdn:ip:ttl:timestamp:lo"
    '''    
    * an A record showing ip as the IP address of fqdn and
    * a PTR (``pointer'') record showing fqdn as the name of d.c.b.a.in-addr.arpa if ip is a.b.c.d. 
    '''

class ForwardARecord(DnsRecord):
    FORMAT = "+fqdn:ip:ttl:timestamp:lo"
    '''    
    * an A record showing ip as the IP address of fqdn 
    '''
    
class MxRecord(DnsRecord):
    FORMAT = "@fqdn:ip:x:dist:ttl:timestamp:lo"
    '''
    * an MX (``mail exchanger'') record showing x.mx.fqdn as a mail exchanger for fqdn at distance dist and
    * an A record showing ip as the IP address of x.mx.fqdn. 
    '''            
    
class IgnoreRecord(DnsRecord):
    FORMAT = "-fqdn:ip:ttl:timestamp:lo"
    '''    
    Record is ignored, but kept in the database all the same.
    '''
    
class TextRecord(DnsRecord):
    FORMAT = "'fqdn:s:ttl:timestamp:lo"
    '''  TXT Record of string 's'
    '''
    
    
class PtrRecord(DnsRecord):
    FORMAT = "^fqdn:p:ttl:timestamp:lo" 
    '''
    PTR record for fqdn. tinydns-data creates a PTR record for fqdn pointing to the domain name p. 
    '''
        
class CnameRecord(DnsRecord):
    FORMAT = "Cfqdn:p:ttl:timestamp:lo"
    ''' 
    CNAME (``canonical name'') record for fqdn. tinydns-data creates a CNAME record for fqdn pointing to the domain name p. 

    '''

class SimpleSoaRecord(DnsRecord):
    FORMAT = "Zfqdn:mname:rname:ser:ref:ret:exp:min:ttl:timestamp:lo"
    '''
    SOA record for fqdn showing: 
    
    mname as the primary name server, 
    rname (with the first . converted to @) as the contact address, 
    ser as the serial number, 
    ref as the refresh time, 
    ret as the retry time, 
    exp as the expire time, and 
    min as the minimum time. 
    
    ser, ref, ret, exp, and min may be omitted; 
    they default to, respectively, the modification time of the data file, 16384 seconds, 2048 seconds, 1048576 seconds, and 2560 seconds. 
    
    '''
    
class GenericRecord(DnsRecord):
    FORMAT = ":fqdn:n:rdata:ttl:timestamp:lo"
    '''
    Generic record for fqdn. tinydns-data creates a record of type n for fqdn showing rdata. 
    n must be an integer between 1 and 65535; it must not be 2 (NS), 5 (CNAME), 6 (SOA), 12 (PTR), 15 (MX), or 252 (AXFR). 
    The proper format of rdata depends on n. You may use octal \nnn codes to include arbitrary bytes inside rdata. 
    '''
    
    
    
    
    
    
    