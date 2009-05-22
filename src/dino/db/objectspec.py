import re
    
import sqlalchemy.orm.properties as sa_props
import sqlalchemy.orm 

from dino.config import class_logger    
from exception import * 

__all__ = [ 'ObjectSpec', 'EntityName', 'EntityQuery', 
            'ElementSpec', 'ElementName', 'ElementId', 'ElementFormId', 
            'ElementQuery', 'AttributeSpec', 'AttributeName',
            ]
 
 
class ObjectSpec(object):
    ''' ObjectSpec is a string that specifies one or more Objects in the database:
    
        - An Entity (EntityName)    
        - An Element   (ElementName, ElementId, ElementFormId)
        - An Attribute on an Element  (AttributeName) 
        
        - A set of Element(s) (ElementQuery)
        - An Attribute on one or more Element(s)  (AttributeQuery) 
        
        - (experimental) Output of a method on an Entity (EntityMethod)
        - (experimental) Output of a method on an Element (ElementMethod)
        
        The name takes the form of:
        
        ObjectSpec := <EntityName> | <ElementSpec> | <AttributeName> | <ElementQuery> 
        
        ElementSpec:= <ElementName> | <ElementId> | <ElementFormId>
        
        --Name--
        
        EntityName := <String> 
            Name of Entity Class (Device, Subnet, Site, etc)
        
        ElementName := <EntityName> / <InstanceName> 
            User-Readable name of Element
                
            InstanceName := Unique, Human readable name based on the data in the instance 

        ElementId := <EntityName> / <InstanceId> 
            Databse Id based name of Element 
             
            InstanceId := '{' num '}'  Unique Integer id based on the unique id column in the database
        
        ElementFormId := <EntityName> / <FormId>
            Temporary Form based name of Element
        
            FormId :=  '<' num '>' Unique Integer within a given form context.  

        AttributeName := { <ElementName> | <ElementId> } / <PropertyName>            
            
            
            
        --Query--
        
        ElementQuery := <EntityName> '[' <QuerySpec> ']'
        
        -- AttributeQuery := <ElementQuery>/<PropertyName>  --
         
        QuerySpec := <QueryClause>[';'<QueryClause>[ ... ] ]
        
        QueryClause := <JoinClause> | <JoinFilterClause> | <ObjectFilterClause>

            JoinClause := <ElementName>  
    
            JoinFilterClause := <ElementName>.<PropertyName>=<value> 
    
            ObjectFilterClause := <PropertyName>=<value> 
        
        
        
        -- Examples --

        EntityName
            Device
            Subnet

        ElementName:
            Device/001EC9437ABF
            Site/sjc1
        
        ElementId:
            Device/{12}
            Site/{304}
            
        ElementFormId:
            Device/<2>
            Port/<1>
            
        AttributeName
            Device/001EC9437ABF/notes
            Site/sjc1/name

        ElementQuery
            Device[hw_class=server]   # ObjectFilterClause
            Host[device.hw_class=server]  # JoinFilterClause
            Host[device;chassis.name=unknown]  # JoinClause + JoinFilterClause
        
        AttributeQuery
            Device[hw_class=server]/name
            Host[device;chassis.name=unknown]/device
        
    '''
    
    SEPARATOR = '/'    
    

    @staticmethod
    def spec_types():
        return (AttributeSpec, ElementSpec, EntitySpec)
         
         
    @classmethod
    def parse(cls, object_spec, expected=None):
        ''' Parse a object_spec and return an appropriate object'''   
        
        assert object_spec is not None, "object_spec cannot be empty"   
        if not isinstance(object_spec, basestring): 
            raise ObjectSpecError(object_spec, "ObjectSpec.parse() argument must be string. Got %s" % type(object_spec))
                
        for class_ in cls.spec_types():            
            result = class_._process(object_spec)
            if result is not None:                    
                cls.check_expected(object_spec, result.__class__, expected)
                return result
                
        return None
        
        
    @classmethod
    def _process(cls, element_spec, expected=None):        
        for class_ in cls.spec_types():
            if class_.matches(element_spec):
                return class_.create(element_spec, expected)
                    
        return None
            

    @classmethod
    def matches(cls, object_spec):
        if hasattr(cls, 'REGEX'):
            return cls.REGEX.match(object_spec) is not None                       
        else:
            return False

    @classmethod
    def create(cls, object_spec, expected=None):        
        m = cls.REGEX.match(object_spec)
        cls.check_expected(object_spec, cls, expected)
        return cls(*m.groups())
    
    
    @classmethod
    def check_expected(cls, object_spec, class_, expected):
        if expected is None:
            return 
        if not isinstance(expected, (list, tuple)):
            expected = (expected, )
                             
        if class_ not in expected:
            expected_strs = [ c.__name__ for c in expected ]
            raise ObjectSpecError(object_spec, "Expected type: %s but result was type: %s"  % (expected_strs, class_.__name__))
                          
    @classmethod
    def is_spec(cls, str_arg):
        assert isinstance(str_arg, basestring), "argument is not a string?: %s" % type(str_arg)
        if hasattr(cls, 'REGEX'):            
            return cls.REGEX.match(str_arg) is not None

        for c in cls.spec_types():
            if c.is_spec(str_arg):
                return True
        
        return False
            
            
    @classmethod
    def create_element_regex(self, name):
        '''
        Return a compiled RegEx object that will exactly match 
        a ElementName string for the EntityName specified by Name
        
        The Groups within the match object are  (eg Device/foo)
        
        1: The ElementName : 'Device/foo'   (remove any single quotes)
        2: The EntityName : 'Device'
        3: The InstanceName : 'foo' 
        '''
        return re.compile("[']*((%(name)s)/(%(inst)s))[']*" 
            % { 'name' : name, 'inst' : ElementSpec.INSTANCE_NAME })


    def resolve(self, session, **kwargs):
        ''' Resolve the ObjectSpec to the object(s) specified using the specified session.
        
        Every ObjectSpec specifies a one or more Object Instances (Entity Class, Element instance, Attribute value ) .
        Resolve uses the session to return a Generator to iterate over these.
        '''
        raise NotImplemented()
    
    @property
    def object_name(self):
        raise NotImplemented()
    
    def __str__(self):
        return self.object_name
        
        
class_logger(ObjectSpec)       

class EntitySpec(ObjectSpec):
    ENTITY_NAME = '([A-Za-z]+)'

    @staticmethod
    def spec_types():
        return (EntityQuery, EntityName)

        
    def __init__(self, entity_name):            
        self.entity_name = entity_name


#class EntityAll(EntitySpec):
#    REGEX = re.compile("^elements$" % EntitySpec.ENTITY_NAME, re.IGNORECASE)
    

    
class EntityName(EntitySpec):
    '''ObjectSpec to specify a single Element'''
    REGEX = re.compile("^%s$" % EntitySpec.ENTITY_NAME)

    @property   
    def object_name(self):
        return self.entity_name

    def resolve(self, session, **kwargs):
        if self.entity_name.lower() == "element":
            for entity in session.entity_iterator(revisioned=False):
                yield entity
        else:
            yield session.resolve_entity(self.entity_name)


class EntityQuery(EntitySpec):   
    REGEX = re.compile("^%s/$" % EntitySpec.ENTITY_NAME)

    
    def __str__(self):
        return self.entity_name
    
    def resolve(self, session, **kwargs):
        instances = kwargs.get('instances', True)
        revisioned = kwargs.get('include_revisioned', False)
        
        if self.entity_name.lower() == "element":
            entity_list = session.entity_iterator(revisioned=False)
        else:
            entity_list = [ session.resolve_entity(self.entity_name) ]
        
        for entity in entity_list:
            if instances:
                for inst in session.query(entity).all():
                    yield inst
            else:
                yield entity





class_logger(EntityName)       

class ElementSpec(ObjectSpec):
    INSTANCE_NAME = '([^/\s,\'\<\{][^/\s,\']*[^/\s,\'\>\}]?)'
    INSTANCE_ID = '\{(\d+)\}'
    INSTANCE_FORM_ID = '\<(\d+)\>'
    QUERY_CLAUSE = '([\w;_.=]*)'


    @staticmethod
    def spec_types():
        return (ElementName, ElementId, ElementFormId, ElementQuery)

    @classmethod
    def create(cls, element_spec, expected=None):
        m = cls.REGEX.match(element_spec)
        (entity_spec, instance_spec) = m.groups()
        entity_spec = EntitySpec._process(entity_spec)
        
        if entity_spec is not None:
            cls.check_expected(element_spec, cls, expected)
            return cls(entity_spec, instance_spec)
        

    @property
    def entity_name(self):
        return self.entity_spec.entity_name
        
    @property
    def object_name(self):
        return self.SEPARATOR.join((str(self.entity_spec), self.instance_spec))
            
            
            
class ElementName(ElementSpec):
    REGEX = re.compile("^(.*)/%s$" % ElementSpec.INSTANCE_NAME)
    
    def __init__(self, entity_spec, instance_name):            
        self.entity_spec = entity_spec
        self.instance_name = instance_name
    
    @property
    def instance_spec(self):
        return self.instance_name
        
    def resolve(self, session, **kwargs):
        for entity in self.entity_spec.resolve(session, **kwargs):        
            element = session.query(entity).filter_by(instance_name=self.instance_name).limit(1).first()
            if element is None:
                raise UnknownElementError(self.object_name)
            else:
                yield element

class_logger(ElementName)       



class ElementId(ElementSpec):
    ''' '''
    REGEX = re.compile("^(.*)/%s$" % ElementSpec.INSTANCE_ID) 
    
    def __init__(self, entity_spec, instance_id):
        self.entity_spec = entity_spec
        self.instance_id = long(instance_id)                   
    
    def resolve(self, session, **kwargs):
        for entity in self.entity_spec.resolve(session, **kwargs):
            yield session.query(entity).filter_by(id=self.instance_id).limit(1).first()
    
    @property
    def instance_spec(self):
        return "{%d}" % int(self.instance_id)
        
    @staticmethod
    def to_instance_id(id):
        return "{%d}" % int(id)
              
class_logger(ElementId)




class ElementFormId(ElementSpec):
    '''  '''
    REGEX = re.compile("^(.*)/%s$" % ElementSpec.INSTANCE_FORM_ID)
     
    def __init__(self, entity_spec, form_id):
        self.entity_spec = entity_spec
        self.form_id = long(form_id)
    
    def resolve(self, session, **kwargs):
        raise NotImplemented("Cannot resolve ElementFormId")
    
    @property    
    def instance_spec(self):
        return "<%d>" % self.form_id
        
    @staticmethod
    def to_form_id(id):
        return "<%d>" % id

class_logger(ElementFormId)

   


class ElementQuery(ElementSpec): 
    REGEX = re.compile("^(.*)\[%s\]$" % ElementSpec.QUERY_CLAUSE)

    def __init__(self, entity_spec, query_clause):            
        self.entity_spec = entity_spec
        self.query_clause = query_clause
    
        
    def __str__(self):        
        return "%s[%s]" % (str(self.entity_spec), self.query_clause)  
        
    def create_query(self, session, entity):
        '''Process query clauses and generate a SQLAlchemy Query.
        
        QueryClause := <JoinClause> | <JoinFilterClause> | <ObjectFilterClause>
            JoinClause := <EntityName>      
            JoinFilterClause := <EntityName>.<Attribute>=<value>     
            ObjectFilterClause := <Attribute>=<value> 
        '''            
        query = session.query(entity)

        filter = False
        for clause in self.query_clause.split(';'):
            if clause == "":
                continue
            join_entity = None
            target_entity = None
            property_name = None
            value = None
            
            # JoinClause
            if '=' not in clause:
                if '.' in clause:
                    raise QueryClauseError(self, "Cannot specify Attribute with no Value: %s" % clause)               
                join_entity = session.resolve_entity(clause)
                query = query.join(join_entity)
                continue
            
            # JoinFilter
            (property_name, value) = clause.split('=')            
            if '.' in property_name:
                (join_entity_name, property_name) = property_name.split('.')
                join_entity = session.resolve_entity(join_entity_name)
                query = query.join(join_entity)
                attr_obj = self._get_attr_obj(join_entity, property_name)

            # ObjectFilter
            else:                
                attr_obj = self._get_attr_obj(entity, property_name)
            
            if value == "None":
                value = None
            
#            import types
#            if not isinstance(value, (int, long, types.StringTypes, types.NoneType, types.BooleanType):
#                raise  QueryClauseError(self, "Value must be (number, string, boolean, None): %s" % type(value) )
                
            query = query.filter(attr_obj==value)
            filter = True
 
        return query

    def _get_attr_obj(self, class_, property_name):
        if not hasattr(class_, property_name):
            raise QueryClauseError(self, "Invalid PropertyName on Element: %s.%s" % (class_, property_name))
        return getattr(class_, property_name)

    def resolve(self, session, **kwargs):
        print_sql = kwargs.get('print_sql', False)        
        
        for entity in self.entity_spec.resolve(session):
            query = self.create_query(session, entity)                            
            if print_sql:
                yield str(query)
                
            else: 
                for inst in query:
                    yield inst
            
            
class_logger(ElementQuery)  
   

class AttributeSpec(ObjectSpec):
    PROPERTY_NAME = '([^/\s,\']+)'
    
    @staticmethod
    def spec_types():
        return (AttributeName,)
        
    @classmethod
    def create(cls, object_spec, expected=None):
        m = cls.REGEX.match(object_spec)
        (element_spec, property_name) = m.groups()
        element_spec = ElementSpec._process(element_spec, expected=(ElementName, ElementId, ElementQuery))
        if element_spec is not None:             
            return cls(element_spec, property_name)
            
        return None


    @property
    def entity_name(self):
        return self.element_spec.entity_name
    
    @property
    def instance_spec(self):
        return self.element_spec.instance_spec

class_logger(AttributeSpec)  

class AttributeName(AttributeSpec):
    REGEX = re.compile("^(.*)/%s$" % AttributeSpec.PROPERTY_NAME)
    
    def __init__(self, element_spec, property_name):
         self.element_spec = element_spec
         self.property_name = property_name

    @property
    def object_name(self):
        return self.SEPARATOR.join((str(self.element_spec), self.property_name))
    
    
    def resolve(self, session, **kwargs):  
        for inst in self.element_spec.resolve(session, **kwargs):
            yield inst.attribute(self.property_name)
            
class_logger(AttributeName)  


class AttributeQuery(AttributeSpec):
    ''' Currently unused '''
    def __init__(self, element_query, property_name):
         self.element_query = element_query
         self.property_name = property_name

    @property
    def object_name(self):
        return self.SEPARATOR.join((str(self.element_query), self.property_name))
    
    
    def resolve(self, session, **kwargs):  
        for inst in self.element_query.resolve(session, **kwargs):
            yield inst.attribute(self.property_name)

class_logger(AttributeQuery)   





