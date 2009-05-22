
import array
import struct        

class PacketBuffer(object):
    def __init__(self, data):
        self._bytes = array.array('B', data)
        
    def bytes(self):
        return self._bytes

    def size(self):
        return len(self._bytes)

    def byte(self, index):
        "Return byte at 'index'"
        return self._bytes[index]

    def word(self, index):
        bytes = self._bytes[index:index+2]        
        (value,) = struct.unpack('!H', bytes.tostring())
        return value

    def long(self, index):
        bytes = self._bytes[index:index+4]
        (value,) = struct.unpack('!L', bytes.tostring())
        return value


class HeaderMeta(type):
    def __init__(cls, name, bases, dict_):        
        super(HeaderMeta, cls).__init__(name, bases, dict_) 
        
        cls.PAYLOADS = {}
        
        if dict_.has_key("CONTAINERS"):
            assert isinstance(dict_["CONTAINERS"], dict)
            for (container_cls, key) in dict_["CONTAINERS"].items():
                assert issubclass(container_cls, Header)                
                container_cls.PAYLOADS[key] = cls

class ParentAttributeError(AttributeError):
    pass

class Header(object):
    __metaclass__ = HeaderMeta
    
    def __init__(self, parent, buffer, index):
        self.buffer = buffer
        self.index = 0
        self.parent = parent
        self.child = None

    def __getattr__(self, attr):        
        """ If this header instance does not have the attribute, try the parent instance"""
        return self._find_parent_attr(attr, path=[])

    def _find_parent_attr(self, attr, path=[]):        
        path.append(self.__class__.__name__)
        if self.parent:                   
            try: 
                return object.__getattribute__(self.parent, attr)
            except AttributeError:
                return self.parent._find_parent_attr(attr, path)
        else:
            search_path = ", ".join(path)
            raise ParentAttributeError("No object in search list (%s) has attribute '%s'" % (search_path, attr))
    
        
    @staticmethod
    def hex2str(bytes):
        if not hasattr(bytes, "__iter__"):
            bytes = [bytes]
        return "0x" + ''.join(map(lambda x: "%02x" % x, bytes))        

    @staticmethod
    def hex2int(bytes):        
        value = 0
        length = len(bytes)
        for (i,x) in enumerate(bytes):
            idx = length-i-1
            value += x << idx*8            
        return value

    @classmethod
    def find_payload_type(cls, payload_key):
        if cls.PAYLOADS.has_key(payload_key):            
            return cls.PAYLOADS[payload_key]
        else:
            return None

    def parse_child(self, key, idx):
        #key_str = ":".join( map(lambda x: "0x%02x" % x, key) )
        #print "%s: KEY: %s" % (self.__class__.__name__, key_str)
        payload_cls = self.find_payload_type(key)
        if payload_cls:
            self.child = payload_cls(self, self.buffer, idx)
    
    def contains_header(self, cls):
        return self.find_header(cls) is not None        

    def find_header(self, cls):        
        if self.child is None or isinstance(self.child, cls):
            return self.child
        else:
            return self.child.find_header(cls)
        


    
