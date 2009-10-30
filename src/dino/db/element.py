import types
import logging
import re
import datetime

import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props

import elixir

from dino import class_logger
from exception import *
from objectresolver import *
from objectresolver import BaseElementResolver
from display import FormDisplayProcessor, EntityDisplayProcessor
import extension

import pprint; pp = pprint.PrettyPrinter(indent=2).pprint

__all__ = [ 'Element', 'ResourceElement', 'InstanceName', 'ElementProperty' ]

###################################################################
#
#
# Element
#
#
###################################################################



class ElementMeta(elixir.EntityMeta):
    ''' Add logger to all Element classes '''

    def __init__(cls, name, bases, dict_):
        elixir.EntityMeta.__init__(cls, name, bases, dict_)

        cls.log = logging.getLogger("dino.db.schema." + name)

        # If none of the base classes are 'derived' from ElementMeta, 
        # this class is the 'Root' (ie Element)
        element_bases = [ b for b in bases if isinstance(b, ElementMeta) ]
        if len(element_bases) == 0:
            return

        cls.NEXT_FORM_ID = 0

        if hasattr(cls, '_descriptor'):
            cls.entity_set = cls._descriptor.collection
            cls._descriptor.add_mapper_extension(extension.ValidateElementMapperExtension())

    def allocate_form_id(cls):
        cls.NEXT_FORM_ID += 1
        return ElementFormIdResolver.to_form_id(cls.NEXT_FORM_ID)

    def entity_display_processor(cls):
        return EntityDisplayProcessor()

    def __str__(cls):
        return cls.__name__


class Element(object):
    """ Base Class for 'most' objects in the Dino Model

    A collection of common instance methods, some taken from elixir.Entity.
    See:
    http://elixir.ematia.de/trac/wiki/FAQ#HowdoIaddfunctionalitytoallmyentitiestothebaseclass
    and
    http://elixir.ematia.de/trac/wiki/FAQ#HowdoIprovideadifferentbaseclassthanEntity

    """
    __metaclass__ = ElementMeta

	# Default Display Processor used for 'show' command
	# Override in subclasses for different behavior
    DISPLAY_PROCESSOR = FormDisplayProcessor

    #
    # All Elements have an InstanceName
    #

    @classmethod
    def has_revision_entity(cls):
        return hasattr(cls, 'Revision')

    @classmethod
    def is_revision_entity(cls):
        return hasattr(cls, '__main_entity__')

    @classmethod
    def create_empty(cls):
        return cls()

    @classmethod
    def display_processor(cls):
        return cls.DISPLAY_PROCESSOR()

    def existing(self):
        return self.id is not None

    @property
    def entity(self):
        return self.__class__

    @property
    def entity_name(self):
        return self.__class__.__name__


    def __init__(self, **kwargs):
        # initialize self._form_id (without calling self.__setattr__())
        object.__setattr__(self, '_form_id', None)
        self.set(**kwargs)

    def __str__(self):
        return self.element_name

    def set(self, **kwargs):
        for key, value in kwargs.iteritems():
            attr = self.__class__.__dict__.get(key)
            if attr is None:
                raise RuntimeError("Set() passed Key that is not valid: %s" % key)
            if not isinstance(attr, sa_orm.attributes.InstrumentedAttribute):
                raise RuntimeError("Set() passed Key that is not InstrumentedAttribute: %s" % key)

            setattr(self, key, value)

    def validate_element(self):
        ''' Called just before insert / update.  
        Used to validate the contents of the element, before allowed into the database
        '''
        pass

    def __setattr__(self, name, value):
        if not hasattr(self, name) and name not in ('_sa_instance_state', '_default_state', '_changeset_view'):
            self.log.warning("Assigning to unknown attribute: %s.%s" % (self.__class__.__name__, name))
        object.__setattr__(self, name, value)


    def get_path(self, path):
        ''' Return a value (object or value) for a path. 
        
        Path is either a string of '.' separated property names 
            Ex. 'device.rack.site' 
            
        or tuple of property name strings
            Ex. ('device', 'rack', 'site')        
        '''
        if isinstance(path, basestring):
            path = tuple(path.split('.'))

        def _path_to_value(instance, path):
            ''' Recursively resolve the path of attributes, returning the last value'''
            if not hasattr(instance, path[0]):
                raise ElementException("Invalid property name in path: %s" % path[0])
            value = getattr(instance, path[0])

            if len(path) > 1 and value is not None:
                return _path_to_value(value, path[1:])

            return value

        return _path_to_value(self, path)



    @classmethod
    def has_sa_property(cls, property_name):
        return cls.mapper.has_property(property_name)

    @classmethod
    def get_sa_property(cls, name):
        '''Return the SqlAlchemy property (sqlalchemy.orm.properties.Property)
            for a given attribute/relation specified by name'''
        return cls.mapper.get_property(name, raiseerr=False)

    @classmethod
    def get_sa_property_type(cls, name):
        '''Return the type_info for a given property.
        For Column properties:
            Return SqlAlchemy type (instance of sqlalchemy.types.AbstractType)
        For Relation properties:
            Return 
            - target class, or 
            - list with the target class as the single element (for list relations)          
        '''
        sa_property = cls.mapper.get_property(name)

        if isinstance(sa_property, sa_props.ColumnProperty):
            return sa_property.columns[0].type

        elif isinstance(sa_property, sa_props.RelationProperty):
            if isinstance(sa_property.argument, sa_orm.Mapper):
                target_cls = sa_property.argument.class_
            else:
                target_cls = sa_property.argument

            return target_cls

    @classmethod
    def get_sa_property_by_type(cls, target_type):
        ''' Find the first property on this class which has a target type of the target entity
        Host.get_property_by_target_entity(Device) -> 'device'
        '''
        for sa_property in cls.mapper.iterate_properties:
            if isinstance(sa_property, sa_props.ColumnProperty):
                if sa_property.columns[0].type == target_type:
                    return sa_property

            if isinstance(sa_property, sa_props.RelationProperty):

                if isinstance(sa_property.argument, sa_orm.Mapper):
                    prop_target_class = sa_property.argument.class_
                else:
                    prop_target_class = sa_property.argument

                if prop_target_class == target_type:
                    return sa_property

        return None

    #
    # ElementName Related Methods
    #

    @classmethod
    def element_name_regex(cls):
        '''Return a compiled RegEx object that will 
        match an ElementName of this objects type.
        
        The Groups within the match object are  (eg Device/foo)
        
        1: The ElementName : 'Device/foo'   (if the string has single quotes, they are removed)
        2: The EntityName : 'Device'
        3: The InstanceName : 'foo' 
        '''
        if 'ELEMENT_NAME_REGEX' not in vars(cls):
            cls.ELEMENT_NAME_REGEX = BaseElementResolver.create_element_name_regex(cls.__name__)
        return cls.ELEMENT_NAME_REGEX



    @property
    def instance_id(self):
        if self.id:
            return ElementIdResolver.to_instance_id(self.id)
        else:
            return None

    def element_property(self, property_name):
        if not self.has_sa_property(property_name):
            raise ElementPropertyError("Attribute not found on Element: %s : %s" % (self, property_name))

        sa_property = self.get_sa_property(property_name)

        if isinstance(sa_property, sa_props.ColumnProperty):
            return ElementPropertyColumn(self, property_name)

        elif isinstance(sa_property, sa_props.RelationProperty):
            if sa_property.uselist:
                return ElementPropertyRelationToMany(self, property_name)
            else:
                return ElementPropertyRelationToOne(self, property_name)

        else:
            raise ElementPropertyError()

    @property
    def element_name(self):
        return ElementNameResolver.make_name(self.entity_name, self.instance_name)

    @property
    def element_id(self):
        if self.id:
            return ElementIdResolver.make_name(self)
        else:
            return None


    def find_name(self):
        ''' Find some unique name by which to refer to this instance
        1. Look at the instance_name column (None if a required field is not available)
        2. Look at the InstanceId from the id column of the object (None if the object has never been persisted) 
        3. Look at existing form_id value 
        4. Create a temporary FormId unique to all instances of this Element, in this process         
        '''

        self.log.finest("  Trying instance_name")
        instance_name = self.instance_name

        if instance_name is None:
            self.log.finest("  Trying instance_id")
            instance_name = self.instance_id

        if instance_name is None:
            self.log.finest("  Trying form_id")
            instance_name = self._form_id

        if instance_name is None:
            self.log.finest("  Allocating form_id")
            instance_name = self._form_id = self.__class__.allocate_form_id()

        self.log.finest("  InstanceName: %s" % instance_name)

        return instance_name


    def derive_name(self):
        return self.NAME_PROCESSOR.derive_name(self)

    def derive_element_name(self):
        return str(ElementNameResolver.make_name(self.entity_name, self.derive_name()))

    def update_name(self, override_dict={}):
        derived_name = self.NAME_PROCESSOR.derive_name(self, override_dict)
        self.log.fine("UPDATE: %s %s", repr(self), derived_name)
        if self.instance_name != derived_name:
            self.instance_name = derived_name
            self.log.info("Updating: %s", self.instance_name)
            return True
        else:
            return False

    @classmethod
    def update_all_names(cls, session):
        if cls is Element:
            entity_list = session.entity_iterator()
        else:
            entity_list = (cls,)

        for entity in entity_list:
            cls.log.info("Processing: %s" % entity.__name__)

            for elmt in session.query(entity).all():
                elmt.update_name()

class ResourceElement(object):
    '''  What is a 'ResourceElement'?
    A ResourceElement is an Element that can be created completely
    from a single string value
    
    
    ResourceElement Constraints (still in progress):
    1. Must be able to create from a single string argument
    2. May be attached to a parent_instance that it has a relation to
    3. May be require a parent to persist. (if it has no parent, it will be deleted on flush())

    Example: IpAddress:
    newip = IpAddress.create_resource(session, "172.31.120.100")
    '''

    @classmethod
    def create_resource(self, session, value, related_instance=None):
        '''Rreate a "ResourceElement" instance from the value
        value: string used to create the resource
        related_instance: instance the resource will be assigned to.
        '''
        raise NotImplemented()




class ElementProperty(object):
    ''' 
    An Attribute is a specific attribute on a specific element instance
    '''

    PARSER_MAP = {
        sa_types.Boolean : bool,
        sa_types.Integer : int,
        sa_types.String : str,
        sa_types.Text : str,
        sa_types.Unicode : unicode,
        sa_types.Float : float,
        sa_types.Date : datetime.date,
        sa_types.DateTime : datetime.datetime,
        sa_types.Time : datetime.time,
        sa_types.Interval : datetime.timedelta,
    }

    def __init__(self, element, name):
        assert self.__class__ is not ElementProperty, "Hey! use a subclass of ElementProperty"

        self.element = element
        self.property_name = name
        self.sa_property = self.element.get_sa_property(self.property_name)


    def __str__(self):
        return self.element_property_name()

    def element_property_name(self):
        return PropertySpecResolver.make_name(self.element.entity_name, self.element.instance_name, self.property_name)

    def is_relation(self):
        return isinstance(self.sa_property, sa_props.RelationProperty)

    def is_attribute(self):
        return isinstance(self.sa_property, sa_props.ColumnProperty)

    def is_relation_to_one(self):
        return self.is_relation() and not self.sa_property.uselist

    def is_relation_to_many(self):
        return self.is_relation() and self.sa_property.uselist

    def value(self):
        '''return the value specified by this Attribute object'''
        return getattr(self.element, self.property_name)

    def valuestr(self):
        return str(self.value())

    def _resolve_value_element(self, value):
        '''Given a string (resource or object specification), return an element
            
        '''

        if isinstance(value, Element) or value is None:
            return value

        target_cls = self.element.get_sa_property_type(self.property_name)

        try:
            session = sa_orm.object_session(self.element)
            assert session is not None, "Element must be attached to session to use set"

            value_element = session.resolve_element_spec(value)

            if not isinstance(value_element, target_cls):
                raise ElementPropertyError("Object Specification resolves to incorrect type %s.  Must resolve to type %s" % (type(value_element), target_cls))

        except InvalidObjectSpecError, e:

            if issubclass(target_cls, ResourceElement):
                self.log.finer("Create Resource from value: %s" % value)
                value_element = target_cls.create_resource(session, value, self.element)

            else:
                raise ElementPropertyError("Must specify ElementName/ElementId for . Argument cannot be resolved: %s", value)

        return value_element


    def add(self, value):
        raise ElementPropertyError("Cannot only call ElementProperty.add() on ElementProperty is OneToMany / ManyToMany")

    def remove(self, value):
        raise ElementPropertyError("Cannot only call ElementProperty.remove() on ElementProperty is OneToMany / ManyToMany")

    def set(self, value):
        raise NotImplemented()


class ElementPropertyColumn(ElementProperty):

    def set(self, value):
        # Method returns a processor for converting between SQL and Python types
        coltype_processor = self.sa_property.columns[0].type
        # We want to know what class the type processor came from, and translate 
        # to a python type.        
        coltype = type(coltype_processor)

        if value is None:
            value = ""

        elif value == 'None':
            value = None

        elif coltype in self.PARSER_MAP:
            try:
                value_type = self.PARSER_MAP[coltype]
                value = value_type(value)

            except ValueError, e:
                raise ElementPropertyError("Bad Value for Column: %s Type: %s Value: %s" % (self.element_property_name(), str(value_type), value))

            except TypeError, e:
                raise ElementPropertyTypeError(self.element, self.property_name, value)

        setattr(self.element, self.property_name, value)


class ElementPropertyRelationToOne(ElementProperty):

    def set(self, value):
        if value == "None":
            value = None

        value = self._resolve_value_element(value)
        setattr(self.element, self.property_name, value)


class ElementPropertyRelationToMany(ElementProperty):

    def valuestr(self):
        return "[" + " ".join([ str(x) for x in self.value()]) + "]"

    def set(self, value):
        assert isinstance(value, (basestring, list, Element)), "Must Element pass element, list or string to ElementProperty.set() for this property: %s" % str(self)

        property_collection = getattr(self.element, self.property_name)

        if isinstance(value, (basestring, Element)):
            value = self._resolve_value_element(value)
            property_collection.append(value)

        elif isinstance(value, (list, set, types.GeneratorType)):
            value_collection = [ self._resolve_value_element(v) for v in value ]

            # make the property collection look like the value collection
            for elmt in property_collection:
                if elmt not in value_collection:
                    property_collection.remove(elmt)

            for elmt in value_collection:
                if elmt not in property_collection:
                    property_collection.append(elmt)


    def add(self, value):
        if not self.is_relation_to_many():
            raise ElementPropertyError("Cannot only call ElementProperty.add() on ElementProperty is OneToMany / ManyToMany")

        value = self._resolve_value_element(value)

        property_collection = getattr(self.element, self.property_name)
        if not isinstance(property_collection, list):
            raise ElementPropertyError("""Cannot currently call 'add' on an ElementProperty OneToMany/ManyToMany that is not a list""")


        if value not in property_collection:
            property_collection.append(value)
        else:
            raise ElementPropertyError("Element not added: Element already on list: %s", value)



    def remove(self, value):
        value = self._resolve_value_element(value)

        property_collection = getattr(self.element, self.property_name)
        if not isinstance(property_collection, list):
            raise ElementPropertyError("""Cannot currently call 'remove' on an ElementProperty OneToMany/ManyToMany that is not a list""")

        if value in property_collection:
            property_collection.remove(value)
        else:
            raise ElementPropertyError("Cannot remove: Element not in list: %s", value)


class_logger(ElementProperty)
