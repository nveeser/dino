#!/usr/bin/env python

import sys
from elixir.py23compat import rsplit
from exception import *

class MultiMap(dict):
    def __setitem__(self, key, value):     
        current = dict.__setitem__(self, key, value)
        if current:
            if isinstance(current, list):
                current.append(value)
            else:
                dict.__setitem__(self, key, [current, value])
        else:
            dict.__setitem__(self, key, value)
        
    def __delitem__(self, key):
        value = self.__getitem__(key)
        if isinstance(value, list):
            value.remove(entity)
            if not value:  # list is empty
                dict.__delitem__(self, key)
        else:
            dict.__delitem__(self, key)



class EntityCollection(list):
    def __init__(self):
        list.__init__(self)
        self._map = MultiMap()


    def append(self, entity):
        list.append(self, entity)        
        key = entity.__name__
        self._map[key.lower()] = entity

    def remove(self, entity):
        list.remove(self, entity)  
        key = entity.__name__      
        del self._map[key.lower()]


    def resolve(self, key, entity=None):     
        cls = self.find_entity(key)
        if cls is None:
            raise UnknownEntityError(key)
        else:
            return cls

    def find_entity(self, key):        
        res = self._map.get(key.lower(), None)
        if isinstance(res, list):
            raise UnknownEntityError("'%s' resolves to several entities, you should "
                            "use the full path (including the full module "
                            "name) to that entity." % key)
        
        return res


    def has_entity(self, key):
        return self._map.has_key(key.lower())
            
    def clear(self):
        self._map.clear()
        del self[:]
