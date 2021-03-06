import logging
import re

import sqlalchemy.orm as sa_orm
from sqlalchemy import types as sa_types
import sqlalchemy.orm.properties as sa_props

import elixir

from exception import *
from objectspec import *
from display import FormDisplayProcessor, EntityDisplayProcessor
from extension import ElementMapperExtension, ElementInstrumentationManager, DerivedField

__all__ = [ 'Element', 'ResourceElement' ]

###################################################################
#
#
# Element
#
#
###################################################################

class ElementMeta(elixir.EntityMeta):
    ''' Add logger to all Element classes '''
    
    EXTENSION = ElementMapperExtension()

    def __init__(cls, name, bases, dict_):
        elixir.EntityMeta.__init__(cls, name, bases, dict_) 
                
        cls.log = logging.getLogger("dino.db.schema." + name)    

        base_class_type = type(bases[0])
        if not issubclass( base_class_type, ElementMeta ): 
            # is 'base' class of the Metaclass tree (ie Element)
            cls.ALL_ENTITY_LIST = []
            return 
        
        cls.ALL_ENTITY_LIST.append(cls)
        
        if hasattr(cls, '_descriptor'):
            cls._descriptor.add_mapper_extension(cls.EXTENSION)
            cls.entity_set = cls._descriptor.collection
        
        cls.INSTANCE_NAME_REGEX = ObjectSpec.create_element_regex(name)        
        cls.NEXT_FORM_ID = 0


    def allocate_form_id(cls):
        cls.NEXT_FORM_ID += 1
        return ElementFormId.to_form_id(cls.NEXT_FORM_ID)
        
    def entity_display_processor(cls):
        return EntityDisplayProcessor()

class Element(object):   
    """ Base Class for 'most' objects in the Dino Model
    
    This adds the derived Property 'element_name' to all Elements

    Also collection of common instance methods, some taken from elixir.Entity.
    See:
    http://elixir.ematia.de/trac/wiki/FAQ#HowdoIaddfunctionalitytoallmyentitiestothebaseclass
    and
    http://elixir.ematia.de/trac/wiki/FAQ#HowdoIprovideadifferentbaseclassthanEntity

    """              
    __metaclass__ = ElementMeta	
    __sa_instrumentation_manager__ = ElementInstrumentationManager
    
	# Default Display Processor used for 'show' command
	# Override in subclasses for different behavior
    DISPLAY_PROCESSOR = FormDisplayProcessor
    
    #
    # All Elements have an InstanceName
    #
    
    instance_name = DerivedField(sa_types.String(50), 
        derive_method='derive_name',
        getter_method='find_name',
        nullable=False, unique=True)

    @classmethod
    def has_revision_entity(cls):
        return hasattr(cls, 'Revision')
        
    @classmethod    
    def is_revision_entity(cls):
        return hasattr(cls, '__main_entity__')
    
    @classmethod
    def is_element_name(cls, string):
        for element in cls.ALL_ENTITY_LIST:
            if element.INSTANCE_NAME_REGEX.match(string) is not None:
                return True    
        return False 
            
    
    @classmethod
    def element_name_re(cls):
        '''Return a compiled RegEx object that will 
        match an ElementName of this objects type.
        
        The Groups within the match object are  (eg Device/foo)
        
        1: The ElementName : 'Device/foo'   (if the string has single quotes, they are removed)
        2: The EntityName : 'Device'
        3: The InstanceName : 'foo' 
        '''
        return cls.INSTANCE_NAME_REGEX
        
    
    @classmethod
    def create_empty(cls):
        return cls()
    
    def __init__(self, **kwargs):
        self.set(**kwargs)
        
    def set(self, **kwargs):
        for key, value in kwargs.iteritems():            
            attr = self.__class__.__dict__.get(key)
            if attr is None:
                raise RuntimeError("Set() passed Key that is not valid: %s" % key)
            if not isinstance(attr, sa_orm.attributes.InstrumentedAttribute):
                raise RuntimeError("Set() passed Key that is not InstrumentedAttribute: %s" % key)
                
            setattr(self, key, value)            
    
    def __str__(self):
        return self.element_name

    def __setattr__(self, name, value):
        if not hasattr(self, name) and name not in ('_sa_instance_state', '_default_state'):
            self.log.warning("Assigning to unknown attribute: %s.%s" % (self.__class__.__name__, name))
        object.__setattr__(self, name, value)
    
    def get_sa_property(self, name):
        '''Return the SqlAlchemy property (sqlalchemy.orm.properties.Property)
            for a given attribute/relation specified by name'''        
        return self.mapper.get_property(name, raiseerr=False)                                 
            
    def get_sa_property_type(self, name):
        '''Return the type_info for a given property.
        For Column properties:
            Return SqlAlchemy type (instance of sqlalchemy.types.AbstractType)
        For Relation properties:
            Return 
            - target class, or 
            - list with the target class as the single element (for list relations)          
        '''
        sa_property = self.mapper.get_property(name)
        
        if isinstance(sa_property, sa_props.ColumnProperty):
            return sa_property.columns[0].type
            
        elif isinstance(property, sa_props.RelationProperty):
            if isinstance(sa_property.argument, sa_orm.Mapper):            
                target_cls = sa_property.argument.class_
            else:
                target_cls = sa_property.argument
                
            if property.uselist:
                return list(target_cls)
            else:
                return target_cls
                
    def has_sa_property(self, property_name):
        return self.mapper.has_property(property_name)
    
    def attribute(self, property_name):
        return Attribute(self, property_name)

    @property
    def entity(self):
        return self.__class__

    @property
    def entity_name(self):
        return self.__class__.__name__

    @property
    def element_name(self):
        return str(ElementName(self.entity_name, self.instance_name))

    @property
    def instance_id(self):
        if self.id:
            return ElementId.to_instance_id(self.id)
        else:
            return None
    
    @property
    def element_id(self):
        if self.id:
            return ElementId(self.entity_name, self.id).object_name
        else:
            return None
    
    def existing(self):
        return self.id is not None

    def validate_element(self):
        ''' Called just before insert / update.  
        Used to validate the contents of the element, before allowed into the database
        '''
        pass

    def update_name(self):
        derived_name = self.derive_name()
        if self._instance_name != derived_name:
            #print "OLD: %s" % self._instance_name
            #print "NEW: %s" % derived_name
            self._instance_name = derived_name
            self.log.info("Updating: %s", self._instance_name)
    
    def find_name(self):
        ''' Find some unique name by which to refer to this instance
        
        1. Look in the _instance_name attribute
        2. Create an InstanceId from the id column of the object 
        3. Read the underlying _instance_name Column
        4. Create a temporary FormId unique to all instances of this Element, in this process         
        '''
                
        self.log.finest("  Trying _instance_name")
        instance_name = self._instance_name  # self.derive_name()                

        if instance_name is None:
            self.log.finest("  Trying instance_id")
            instance_name = self.instance_id

        if instance_name is None:
            self.log.finest("  Allocating form_id")
            instance_name = self._instance_name = self.__class__.allocate_form_id()
        
        self.log.finest("  Instance_name: %s" % instance_name)
        return instance_name
    
    
    def derive_element_name(self):
        return str( ElementName(self.entity_name, self.derive_name()) )

    def derive_name(self):
        cls = self.__class__
        if hasattr(cls, "INSTANCE_NAME_ATTRIBUTE"):            
            attr_name = getattr(cls, "INSTANCE_NAME_ATTRIBUTE")
            if not hasattr(self, attr_name):
                raise ElementException("Attribute specified by %s.INSTANCE_NAME_ATTRIBUTE" + 
                    " does not exist: %s" % (cls.__name__, attr_name))
                 
            return getattr(self, attr_name)
        else:
            raise ElementException("Undefined InstanceName for %s: " + 
            "Must define attribute INSTANCE_NAME_ATTRIBUTE or method derive_name(self)", cls)

    @classmethod
    def display_processor(cls):
        return cls.DISPLAY_PROCESSOR()


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


class Attribute(object):
    ''' 
    An Attribute is a specific attribute on a specific element instance
    '''
    def __init__(self, element, name):
        self.element = element
        self.property_name = name
    
    def __str__(self):
        return self.attribute_name()
    
    def attribute_name(self):
        element_spec = ElementName(self.element.entity_name, self.element.instance_name)
        return str( AttributeName(element_spec, self.property_name) )
        
    def value(self):
        '''return the value specified by this Attribute object'''
        return getattr(self.element, self.property_name)

    def set(self, value):
        '''
        Set the attribute to value
        Checks Property information on the Attribute, and resolves
        ElementNames to a live Object Reference
        '''  
        session = sa_orm.object_session(self.element)
        assert session is not None, "Instance must be attached to session to use set"
    
        if not self.element.has_sa_property(self.property_name):
            raise ElementAttributeError("Attribute not found on instance: %s : %s" % (self.element, self.property_name) )
            
        sa_property = self.element.get_sa_property(self.property_name)   
                 
        if isinstance(sa_property, sa_props.ColumnProperty):                                                                
            setattr(self.element, self.property_name, value)      
              
        elif isinstance(sa_property, sa_props.RelationProperty):
            value_instance = session.resolve_element_spec(value)
            setattr(self.element, self.property_name, value_instance)

