'''
Set of SQL Alchemy Extensions used by element
'''
import re

import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props
from sqlalchemy.orm.interfaces import AttributeExtension, InstrumentationManager, MapperExtension
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm.attributes import manager_of_class

from elixir import Field
from elixir.properties import EntityBuilder
from elixir.statements import Statement
from elixir.relationships import Relationship

from dino import class_logger
from session import ElementSession
import element
from exception import ElementInstanceNameError
from objectresolver import ObjectSpecParser, ElementNameResolver, InvalidObjectSpecError

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint

__all__ = ['DerivedField', 'use_element_name' ]



class ElementNameBuilder(EntityBuilder):

    def __init__(self, entity, format, *args, **kwargs):

        assert '__main_entity__' not in vars(entity), "ElementNameBuilder should not be present on Revision Entity: %s" % entity
        assert issubclass(entity, element.Element), "builder only valid on Entity derived from %s: %s" % (element.Element, entity)

        self.entity = entity

        # Create Field
        #
        Field(sa_types.String(100), nullable=False, unique=True).attach(entity, 'instance_name')

        # Create NameProcessor (and for Revision Entity too)
        #
        entity.NAME_PROCESSOR = ElementNameBuilder.InstanceNameDeclarationProcessor(format)

        if hasattr(entity, 'Revision'):
            revision_pattern = "%s@{revision}" % format
            entity.Revision.NAME_PROCESSOR = ElementNameBuilder.InstanceNameDeclarationProcessor(revision_pattern)

        self.add_mapper_extension(self.InstanceNameExtension())

    def finalize(self):
        # Compile so that all properties are created on the mapper
        self.entity.mapper.compile()

        if self.entity.NAME_PROCESSOR.attribute_names:
            self.log.fine("Process DEPENDENCIES: %s", self.entity.__name__)

        for instance_name_key in self.entity.NAME_PROCESSOR.attribute_names:
            parser = ElementNameBuilder.DependParser(self.entity, instance_name_key)

            for (listener_entity, listener_attr, listener) in parser.depend_list:
                listener_manager = manager_of_class(listener_entity)
                listener_manager[listener_attr].impl.extensions.insert(0, listener)



    class InstanceNameExtension(MapperExtension):

        def before_insert(self, mapper, connection, instance):
            assert isinstance(instance, element.Element)
            if instance.instance_name is None:
                raise ElementInstanceNameError("InstanceName cannot be None: %s(%s)" % (mapper.class_, id(instance)))

            # Build a spec parser and see if the instance_name is valid
            try:
                spec_parser = ObjectSpecParser(mapper.class_.entity_set)
                spec_parser.parse(instance.element_name, expected=ElementNameResolver)

            except InvalidObjectSpecError:
                raise ElementInstanceNameError("InstanceName is invalid: %s", instance.element_name)

            return sa_orm.EXT_CONTINUE

        before_update = before_insert

    class ElementNameCacheMapperExtension(MapperExtension):
        def append_result(self, mapper, selectcontext, row, instance, result, **flags):
            self._session(instance).cache_add(instance, "append")
            return sa_orm.EXT_CONTINUE

        def after_insert(self, mapper, connection, instance):
            self._session(instance).cache_add(instance, "insert")
            return sa_orm.EXT_CONTINUE

        def after_update(self, mapper, connection, instance):
            self._session(instance).cache_add(instance, "update")
            return sa_orm.EXT_CONTINUE

        def after_delete(self, mapper, connection, instance):
            self._session(instance).cache_delete(instance)
            return sa_orm.EXT_CONTINUE


        def _session(self, instance):
            session = sa_orm.object_session(instance)
            assert isinstance(instance, element.Element), "Cannot use ElementNameCacheMapperExtension with non Element Entity"
            assert isinstance(session, ElementSession), "Found Element instances with session not derived from ElementSession"
            return session

    class_logger(ElementNameCacheMapperExtension)



    class DependParser(object):
        '''
        For a give spec, more than one AttributeListener may be applied / relevant
        
        Example 1: Host -> 'name' 
            - Host / name / ()
        
        Example 2: Host -> 'site.name'
            
            Adds DependentAttributeListener:  ( Class / Attribute / JoinClause )  
            - Site / name / ( Site, )    
                                  
        Example 3: Host -> 'device.rack.site.name'
            
            Add DependentAttributeListener(s):  ( Class / Attribute / JoinClause )
               
            - Host  / device / ()
                     
            - Device / rack /  ( Device )                                        
            
            - Rack   / site /  ( Device, Rack  )
            
            - Site   / name /  ( Device, Rack, Site )
    
            ie. When update Site.name of Site(id=12), find hosts that are affected.
            The query to find those hosts is specified like:
            session.query(Host).join(Device).join(Rack).join(Site).filter_by(id=site.id)
        '''

        def __init__(self, target_entity, instance_name_key):
            self.target_entity = target_entity
            self.instance_name_key = instance_name_key

            value_path = tuple(instance_name_key.split('.'))

            self.depend_list = self.process_spec(self.target_entity, value_path, ())

        def process_spec(self, listener_entity, value_path, join_tuple):
            self.log.fine("  Process: %s %s %s", listener_entity.__name__, value_path, tuple(x.__name__ for x in join_tuple))

            if len(value_path) == 1:
                listener_attr_name = value_path[0]
                listener = self._create_listener(listener_entity, listener_attr_name, join_tuple)
                return ((listener_entity, listener_attr_name, listener),)

            else:
                (listener_attr_name, next_path) = value_path[0], value_path[1:]

                listener = self._create_listener(listener_entity, listener_attr_name, join_tuple, next_path)

                next_class = listener_entity.get_sa_property_type(listener_attr_name)
                next_join_tuple = (join_tuple + (next_class,))

                next_depends = self.process_spec(next_class, next_path, next_join_tuple)
                return ((listener_entity, listener_attr_name, listener),) + next_depends


        def _create_listener(self, listener_entity, listener_attr_name, join_list, listener_value_path=None):
            self.log.finer("     Listener: %s.%s updates %s value:%s join%s ",
                listener_entity.__name__, listener_attr_name,
                self.target_entity.__name__,
                listener_value_path,
                tuple(x.__name__ for x in join_list))

            return ElementNameBuilder.InstanceNameAttributeListener(self.target_entity, join_list, self.instance_name_key, listener_value_path)

    class_logger(DependParser)


    class InstanceNameAttributeListener(AttributeExtension):
        '''
        Listens to the an attribute on some Element 
        
        target_entity:
            Entity  
            
        join_entity_path:
             list of intermediary Entities to join to, to
        build a query which will specify which specific Element(s) (instance(s)) need to be updated       
        
        target_name_key
            the key used in the InstanceName pattern which has changed
        
        listener_attr_path:
            the attribute path (if any) to retrieve the actually value 
            used in the InstanceName.  
            
            Example:
                Host.instance_name -> {name}.{pod.name}.{device.rack.site.name}
                
                If a Host's Device changes Rack, then the Site name of the Host may change, 
                and thus the Host's instance_name may change.
                
                The attribute to listen to is Device.rack.  The value the listener gets is the new Rack object. 
                The value to use to update the Host's instance_name is not a Rack object, 
                but value of Rack.site.name
                
                In that case, the listener_attr_path is "site.name"
                
        '''
        def __init__(self, target_entity, join_entity_path, target_name_key, listener_attr_path):
            self.target_entity = target_entity
            self.join_entity_path = join_entity_path
            self.target_key_name = target_name_key
            self.value_path = listener_attr_path


        def set(self, state, newvalue, oldvalue, initiator):

            # Find the right value to send to Element.update_name     
            if self.value_path is not None and newvalue is not None:
                assert isinstance(newvalue, element.Element), "assigned value of unexpected type: %s" % type(newvalue)
                update_value = newvalue.get_path(self.value_path)
            else:
                update_value = newvalue

            if self.join_entity_path is ():
                self.update_self(state, update_value, initiator)
            else:
                self.update_dependents(state, update_value, initiator)

            return newvalue

        def update_self(self, state, update_value, initiator):
            self.log.finest("TRIGGER SELF: %s.%s -> %s", initiator.class_.__name__, initiator.key,
                self.target_entity.__name__)

            self.log.finest("   Passed Value: { %s : %s }", self.target_key_name, update_value)

            state.obj().update_name(override_dict={ self.target_key_name : update_value })


        def update_dependents(self, state, update_value, initiator):
            self.log.finest("TRIGGER: %s.%s -> %s via %s %s", initiator.class_.__name__, initiator.key,
                self.target_entity.__name__, tuple(x.__name__ for x in self.join_entity_path), self.value_path)

            session = object_session(state.obj())
            if session is None:
                self.log.finest("   No session on Source Entity: not updating dependent objects")
                return

            self.log.finest("   Passed Value: { %s : %s }", self.target_key_name, update_value)
            for element in self.find_dependent_elements(session, state.obj()):
                element.update_name(override_dict={ self.target_key_name : update_value })


        def find_dependent_elements(self, session, match_instance):
            q = session.query(self.target_entity)
            for join_entity in self.join_entity_path:
                q = q.join(join_entity)

            # Find Elements in the DB
            #
            for element in q.filter_by(id=match_instance.id).all():
                self.log.finest("   Update(DB): %s", repr(element))
                yield element


            # Find (new) Elements in the Session
            #     
            def entity_to_attribute_path(entity, entity_path):
                value_path = (entity.get_sa_property_by_type(entity_path[0]).key,)

                if len(entity_path) > 1:
                    value_path = value_path + entity_to_attribute_path(entity_path[0], entity_path[1:])

                return value_path

            # Change ('Device', 'Rack') into ('device', 'rack') which can be used with get_value()
            join_attribute_path = entity_to_attribute_path(self.target_entity, self.join_entity_path)

            for element in session.new:
                if isinstance(element, self.target_entity) and element.get_path(join_attribute_path) == match_instance:
                    self.log.finer("   Update(Session): %s", repr(element))
                    yield element



    class_logger(InstanceNameAttributeListener)



    class InstanceNameDeclarationProcessor(object):
        NAME_RE = re.compile('{(\w[^}]*)}')
        OPTIONAL_RE = re.compile('(?<!%)\(([^{]*){(\w[^}]*)}([^)]*)\)(?!s)')

        def __init__(self, pattern):
            self.pattern = pattern
            self.attribute_names = set(self._attribute_names(self.pattern))
            self.optional_names = set()

            left = self.pattern.count('(')
            right = self.pattern.count(')')
            if left != right:
                self.log.warn("Parentheses mismatch?: %s", self.pattern)

            self.pattern_list = self._split_conditional_keys((), self.pattern)

            self.pattern_list = list(self.pattern_list)
            self.pattern_list.sort(key=lambda x:-len(x[0])) # sort by length of key tuple


        @staticmethod
        def _attribute_names(pattern):
            for m in ElementNameBuilder.InstanceNameDeclarationProcessor.NAME_RE.finditer(pattern):
                yield m.group(1)

        def _split_conditional_keys(self, key_tuple, pattern):
            '''
            Look for contitional keys and split the pattern into two patterns, 
                one with the conditional supplied 
                one without the contitional supplied.
                recurse...
                
            (),           'FOO(:{optional})' 
            becomes
            (),           'FOO'
            ('optional'), 'FOO:%(optional)s'  
                
            '''
            m = ElementNameBuilder.InstanceNameDeclarationProcessor.OPTIONAL_RE.search(pattern)
            if m:
                (before, optional_key, after) = m.groups()

                self.optional_names.add(optional_key)

                text = before + "%(" + optional_key + ")s" + after

                pattern_with = pattern[:m.start()] + text + pattern[m.end():]
                pattern_without = pattern[:m.start()] + "" + pattern[m.end():]

                result1 = self._split_conditional_keys(key_tuple + (optional_key,), pattern_with)
                result2 = self._split_conditional_keys(key_tuple, pattern_without)

                return result1 + result2

            else:
                return ((key_tuple , self._replace_keys(pattern)),)

        @staticmethod
        def _replace_keys(pattern):
            ''' replace any remaining non-conditional keys in the pattern string with python str refs
            'FOO-{key}' -> 'FOO-%(key)s' 
            '{key1}_{key2} -> '%(key1)s_%(key2)s'
            '''
            m = ElementNameBuilder.InstanceNameDeclarationProcessor.NAME_RE.search(pattern)
            while m:
                pattern = pattern[:m.start()] + "%(" + m.group(1) + ")s" + pattern[m.end():]
                m = ElementNameBuilder.InstanceNameDeclarationProcessor.NAME_RE.search(pattern)
            return pattern


        def make_name(self, value_dict):
            ''' Look up the correct pattern based on which keys are available
            in the dict, and evaluate that string with the value dictionary
            '''

            value_key_set = set(value_dict.keys())
            if len(self.attribute_names - value_key_set) > 0:
                raise RuntimeError("Value_dict missing attribute names: %s" % str(self.attribute_names - value_key_set))

            for name in self.attribute_names - self.optional_names:
                if value_dict[name] is None:
                    return None

            pattern = self._find_pattern(value_dict)

            return pattern % value_dict


        def _find_pattern(self, value_dict):
            for key_tuple, pattern in self.pattern_list:
                availables = [ key for key in key_tuple if value_dict[key] is not None ]

                if len(availables) == len(key_tuple):
                    return pattern

            raise RuntimeError("No Pattern was available.  This should never happen")

        def derive_name(self, instance, override_dict={}):
            values = [ (n, instance.get_path(n)) for n in self.attribute_names ]
            value_dict = dict(values)
            value_dict.update(override_dict)
            return self.make_name(value_dict)





class_logger(ElementNameBuilder)

use_element_name = Statement(ElementNameBuilder)


class ValidateElementMapperExtension(MapperExtension):
    def __new__(cls, *args, **kwargs):
        if '_single' not in vars(cls):
            cls._single = object.__new__(cls, *args, **kwargs)
        return cls._single

    def before_insert(self, mapper, connection, element):
        if hasattr(element, 'validate_element'):
            element.validate_element()
        return sa_orm.EXT_CONTINUE

    def before_update(self, mapper, connection, element):
        self.before_insert(mapper, connection, element)



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

class PropertyClassReference(Relationship):
    pass

