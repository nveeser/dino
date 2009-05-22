'''
Set of SQL Alchemy Extensions used by element
'''

import sqlalchemy.orm as sa_orm
import sqlalchemy.orm.properties as sa_props
from sqlalchemy.orm.interfaces import AttributeExtension, InstrumentationManager, MapperExtension
from sqlalchemy.orm.session import object_session

from elixir import Field

from dino.config import class_logger
from session import ElementSession
#from element import Element
import element
__all__ = ['DerivedField', 'ElementInstrumentationManager', 'name_depends', 'ElementMapperExtension' ]


class IndexedList(list):
    ''' 
    Replacement collection class for SQL Alchemy relations
    
    Behaves just like a list, but addes 'Map-like' traits, indexing items on the list
    using a specified attribute on the child class.
    
    Example
    A Host has Ports
    
    class Host:
        ...
        ports = OneToMany("Port", collection_class=IndexedList.factory('value'))
    
    class Port
        ...
        value = Field(types.String() )
        ...
    
    
    port = Port(name='name1')
    host.ports.append(port)
    host.ports['name1']
    
    
    # Using Mapper
    mapper(Parent, properties={
        children = relation(Child, collection_class=IndexedList.factory('child_attribute'))
    })

    
     
    '''
    
    @staticmethod
    def factory(attr_name):
        def new_list():
            return IndexedList(attr_name)
        return new_list
      
    def __init__(self, attr_name):
        import operator
        list.__init__(self)            
        self.key_func = operator.attrgetter(attr_name)
        self._map = {}
    
    def append(self, item):
        list.append(self, item)
        key = self.key_func(item)             
        if key is not None:
            if self._map.has_key(key) and self._map[key] != item:                
                self.log.warn("Key exists: %s", key)
            else:
                self._map[key] = item        
        return item
    
    def remove(self, item):
        list.remove(self, item)
        
        key = self.key_func(item)
        if key is not None and self._map.has_key(key):
            assert self._map[key] == item 
            del self._map[key]
        
        return item
    
    def rekey(self):
        for item in self:
            key = self.key_func(item)
            self._map[key] = item     
    
    #
    # Map-like functions
    #
    def __getitem__(self, key):
        return self._map[key]
    def __setitem__(self, key, item):
        raise NotImplemented()
    def __delitem__(self, key):
        self.remove(self._map[key])
    
    def keys(self):
        return self._map.keys() 
    def values(self):
        return self._map.values() 
    def items(self):
        return self._map.items()   
    def get(self, key, default=None):
        return self._map.get(key, default)
        
class_logger(IndexedList)

class DerivedField(Field):
    
    """ Like elixir.Field, used to create a property of <name> 
    on an elixir.Entity class.  Unlike elixir.Field, the value 
    is derived from a method specified by the derive_method argument.
    
    Usage:
    class Foo(elixir.Entity):
        <name> = DerivedField( <type>, derive_method=<method_name>, **kwargs)
      
    Like Field, this creates a sqlalchemy.orm.Property 
    on the class called <name>. However, the original 
    sqlalchemy.orm.Property is moved to "_<name>" to be accessed 
    by the mapper extension.  The field value is then stored in the 
    database as a column. The original property is replaced with a python 
    property() instance which derives the value via a defined method.
        
    The schema.Table object (which each Entity has) still contains 
    column called <name>.  This means the original name can still 
    be used in queries with this Entity. 
    """
       
    def __init__(self, type, *args, **kwargs):       
        self.derive_method_name = kwargs.pop('derive_method', None)
        self.getter_method_name = kwargs.pop('getter_method', None)
        self.alt_name = kwargs.pop('alt_name', None)
        super(DerivedField, self).__init__(type, *args, **kwargs)
             
    def before_mapper(self):
        if self.alt_name is None:
            self.alt_name = '_%s' % self.name        
        self.add_mapper_extension(self.DerivedFieldExtension(self.derive_method_name, self.alt_name))
        
    def finalize(self):   
        # !!!!! COMPILE !!!!!
        # Make sure the "mapper" does its magic to the Entity(Class) methods before you 
        # try to override it.  Otherwise the "mapper" will "overwrite" the change.               
        self.entity.mapper.compile()   
        
        derive_method = getattr(self.entity, self.derive_method_name)
            
        if self.getter_method_name:
            public_getter_method = getattr(self.entity, self.getter_method_name) 
        else:             
            public_getter_method = self._create_public_getter(derive_method, self.alt_name)
            
        sa_prop = getattr(self.entity, self.name)
        
        setattr(self.entity, self.name, property(public_getter_method))
        setattr(self.entity, self.alt_name, sa_prop)        
    
    def _create_public_getter(self, derive_method, sa_attr_name):
        def public_getter(self):                        
            value = derive_method(self)
            
            if value is None:
                return getattr(self, sa_attr_name)
            else:                
                return value    
            
        return public_getter

    class DerivedFieldExtension(MapperExtension):
    
        def __init__(self, derive_method_name, sa_field_name):        
            self.derive_method_name = derive_method_name
            self.sa_field_name = sa_field_name
            
        def before_insert(self, mapper, connection, instance):
            derive_method = getattr(instance, self.derive_method_name)             
            setattr(instance, self.sa_field_name, derive_method())            
            return sa_orm.EXT_CONTINUE
        
        before_update = before_insert       
 
class_logger(DerivedField)

def name_depends(*args):
    '''
    Establish dependency between this objects name, and other fields.
    name_depends('<dependant_spec>', ...)
    
    dependant_spec := <Class>.<Field>[;<JoinClass>[;<JoinClass> ...]]
    
    Spec specifes the field to Attribute to watch, and optionally the
    join clause used to find the instances that needs to be updated.
    
    
    Example: 
    
    class Person(Element):
        name = Field(String(60), ...)
        ...
    
    class Address(Element):
        
        @name_depends('Person.name')
        def derive_name(self):
            ...
    
    This means:
      - when *a* Person.name is updated
      - find all *related* Address elements
      - execute address.update_name()    
    '''
    def wrap(func):
        func.__name_depends__ = args
        return func            
    return wrap


class ElementInstrumentationManager(InstrumentationManager):
    MANAGERS = []
    DEP_MAPPING = {}
      
    def __init__(self, class_):
        self.MANAGERS.append(self)
        
        self.class_ = class_
        
        derive_name_func = getattr(class_, "derive_name").im_func        
        self.depend_specs = list(getattr(derive_name_func, '__name_depends__', ()))        

    
    def old_post_configure_attribute(self, class_, key, instr_attr):
        """Add an event listener to an InstrumentedAttribute."""        
        pass
        
    def post_configure_attribute(self, class_, key, instr_attr):
        
        # Process all the dependencies in all managers first.
        # If any other class depends on this one, make sure that class
        # gets its info into DEP_MAPPING, before this class starts
        # looking on that list for attributes
        for manager in self.MANAGERS:
            manager.process_all_depend_specs()
        
        
        if class_.__name__ in self.DEP_MAPPING:
            if key in self.DEP_MAPPING[class_.__name__]:
                self.log.fine("Found key for attribute: ")
                dep_list = self.DEP_MAPPING[class_.__name__].pop(key)
                for class_, join_list in dep_list:
                    listener = self.DependentAttributeListener(self, class_, join_list=join_list)
                    instr_attr.impl.extensions.insert(0, listener)
               


    def process_all_depend_specs(self):        
        while self.depend_specs:
            self._process_depend_spec(self.depend_specs.pop())     


    def _process_depend_spec(self, dep_spec):
        '''
        For a give spec, more than one AttributeListener may be applied / relevant
        
        Example 1: 'Site.name'
            
            Adds Listener:  ( Class / Attribute / JoinClause )  
            - Site / name / ()    
                                  
        Example 2: 'Device;Rack;Site.name'
            
            Add Listener(s):  ( Class / Attribute / JoinClause )            
            - Device / rack /  ()                                        
            
            - Rack / site /  ( Device )
            
            - Site / name /  ( Device, Rack )
        '''

        #print self.log.getEffectiveLevel()
        
        #import pdb;pdb.set_trace()
        self.log.debug("PROCESS: %s", dep_spec)
        
        (join_str, final_attr) = dep_spec.split('.')
        join_names = join_str.split(';')
                
        all_joins = [ self.class_._descriptor.collection.resolve(name) for name in join_names ]
        
        for i, listener_cls in enumerate(all_joins):
            self.log.fine( "  LISTENER CLASS: (%s) %s", i, listener_cls)
                
            if i+1 < len(all_joins):
                next_class = all_joins[i+1] 
                attr_name = self._find_attr_name(listener_cls, next_class)
            else:
                attr_name = final_attr

            join_list = tuple(all_joins[:i])
                
            self.log.fine( "  ADD: %s %s %s", listener_cls, attr_name, join_list)
            self._add_dependency(listener_cls, attr_name, join_list)

    def _find_attr_name(self, listener_cls, next_cls): 
        '''Find the first property name on the listener_cls, 
        that points to the next_class (has next_cls as a target)
        '''        
        for sa_property in listener_cls.mapper.iterate_properties:
            
            if not isinstance(sa_property, sa_props.RelationProperty):
                continue
        
            if isinstance(sa_property.argument, sa_orm.Mapper):            
                prop_target_cls = sa_property.argument.class_
            else:
                prop_target_cls = sa_property.argument
            
            if prop_target_cls == next_cls:
                return sa_property.key
                
       
    def _add_dependency(self, dep_cls, dep_attr, join_list=None): 
        self.DEP_MAPPING.setdefault(dep_cls, {})
        self.DEP_MAPPING[dep_cls].setdefault(dep_attr, [])
        self.DEP_MAPPING[dep_cls][dep_attr].append((self.class_, join_list))        
    
    

            
    class DependentAttributeListener(AttributeExtension):
    
        def __init__(self, manager, target_cls, join_list=None):
            self.manager = manager            
            self.target_cls = target_cls
            
            if join_list is None:
                self.join_list = ()
            else:
                self.join_list = join_list
            
        def set(self, state, value, oldvalue, initiator):
            session = object_session(state.obj())
               
            q = session.query(self.target_cls)
            
            for join_cls in self.join_list:
                q = q.join(join_cls)
                                        
            q = q.join(state.class_).filter_by(id=state.obj().id)
            
            for target in q:
                session.rename_elements.append(target) 
                
            return value

class_logger(ElementInstrumentationManager)



class ElementMapperExtension(MapperExtension):

    
    def append_result(self, mapper, selectcontext, row, instance, result, **flags):
        self._session(instance).cache_add(instance, "append")
        return sa_orm.EXT_CONTINUE
                    
    def before_insert(self, mapper, connection, instance):
        instance.validate_element()
        return sa_orm.EXT_CONTINUE
        
    def before_update(self, mapper, connection, instance):
        instance.validate_element()
        return sa_orm.EXT_CONTINUE
                    
    def after_insert(self, mapper, connection, instance):
        self._session(instance).cache_add(instance, "insert")
        return sa_orm.EXT_CONTINUE
                    
    def after_update(self, mapper, connection, instance):
        self._session(instance).cache_add(instance,"update")
        return sa_orm.EXT_CONTINUE      
              
    def after_delete(self, mapper, connection, instance):
        self._session(instance).cache_delete(instance)
        return sa_orm.EXT_CONTINUE


    def _session(self, instance):
        session = sa_orm.object_session(instance)
        assert isinstance(instance, element.Element), "Cannot use ElementMapperExtension with non Element Entity"
        assert isinstance(session, ElementSession), "Found Element instances with session not derived from ElementSession"                    
        return session
  
class_logger(ElementMapperExtension)
