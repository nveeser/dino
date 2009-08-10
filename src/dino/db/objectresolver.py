import re
import types 
    
import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props
import sqlalchemy.orm 


from dino.config import class_logger    
from exception import * 
import dino.db.element as element





  
class SpecMatchError(ObjectSpecParserError):
    '''Error used by the parser to signal that a 
    resolver does not match the supplied string/spec'''
    def __init__(self, msg):
        self.msg = msg

class Resolver(object):    
    ATTRIBUTE_PATH_SEPARATOR = '/'   
    ELEMENT_NAME_SEPARATOR = ':'
    QUERY_CLAUSE_START = '['
    
    def __init__(self, parser, spec):
        self.parser = parser
                
        if spec.endswith(Resolver.ATTRIBUTE_PATH_SEPARATOR):
            self.resolve_instance = True
            self.spec = spec[: - 1]
        else:
            self.resolve_instance = False
            self.spec = spec
            
            
    def resolve(self, session, **kwargs):
        ''' Resolve the ObjectSpec to the object(s) specified using the specified session.
        
        Every ObjectSpec specifies a one or more Object Instances (Entity Class, Element instance, Attribute value ) .
        Resolve uses the session to return a Generator to iterate over these.
        '''
        raise NotImplemented()

    def get_entity(self):
        ''' Generator that returns the Entity type(s) that this Spec/Name resolves to.  
        
        For a specification that points to an attribute (value), this value is None
        '''
        return self.parent_resolver.get_entity()


class EntityNameResolver(Resolver):
    
    def __init__(self, parser, spec):
        Resolver.__init__(self, parser, spec)
        
        self.parent_resolver = None
        
        #import pdb; pdb.set_trace()
        if self.spec.count(Resolver.ATTRIBUTE_PATH_SEPARATOR) != 0:
            raise SpecMatchError("Entity does have separator: %s" % Resolver.ATTRIBUTE_PATH_SEPARATOR)   
                
        if self.spec.count(Resolver.ELEMENT_NAME_SEPARATOR) != 0:
            raise SpecMatchError("Entity does have separator: %s" % Resolver.ELEMENT_NAME_SEPARATOR)   

        if self.spec.count(Resolver.QUERY_CLAUSE_START) != 0:
            raise SpecMatchError("Entity does have query clause: %s" % Resolver.ELEMENT_NAME_SEPARATOR)   
        
        try:
            if self.spec.lower() == "element":
                self.entity = element.Element
            else:
                self.entity = parser.entity_set.resolve(self.spec)
            
        except UnknownEntityError:
            raise InvalidObjectSpecError("Unknown entity: not found in parser entity_set: %s" % self.spec)        
    
    
    def get_entity(self):
        if self.entity is element.Element:            
            for e in self.parser.entity_set:
                if issubclass(e, element.Element) and not e.is_revision_entity():
                    yield e
                    
        else:
            yield self.entity


    def resolve(self, session, **kwargs):                
        for entity in self.get_entity():             
            if self.resolve_instances:
                for element in session.query(entity).all():
                    yield element
            else:
                yield entity
        

class BaseElementResolver(Resolver):
    def __init__(self, parser, spec):
        Resolver.__init__(self, parser, spec)
        
        m = self.REGEX.match(self.spec)
        if m is None:
            raise SpecMatchError("Spec does not match Syntax")  
        
        self.parent_resolver = parser.parse(m.group(1), expected=EntityNameResolver)    
        self.instance_spec = m.group(2)  
        
        
class ElementQueryResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    QUEUE_CLAUSE = "[^\]]*"
    REGEX = re.compile("^(%s)\[(%s)\]$" % (ENTITY_NAME, QUEUE_CLAUSE))
    
    def __init__(self, parser, spec):
        BaseElementResolver.__init__(self, parser, spec)
        self.query_claus = self.instance_spec

                
    def create_query(self, session, entity):
        '''Process query clauses and generate a SQLAlchemy Query.
        
        QueryClause := <ObjectFilterClause> | <JoinFilterClause> 
            ObjectFilterClause := <Attribute>=<value> 
            JoinFilterClause := [ <JoinClaus>; ] <EntityName>.<Attribute>=<value>     
            JoinClause := [ <JoinClaus>; ] <EntityName>         
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
            (property_name, value) = clause.split('=', 1)            
            if '.' in property_name:
                (join_entity_name, property_name) = property_name.split('.')
                join_entity = self.parser.entity_set.resolve(join_entity_name)
                query = query.join(join_entity)
                attr_obj = self._get_attr_obj(join_entity, property_name)

            # ObjectFilter
            else:                
                attr_obj = self._get_attr_obj(entity, property_name)
            
            if value == "None":
                value = None
              
            query = query.filter(attr_obj == value)
            filter = True
 
        return query
        
        
    def resolve(self, session, **kwargs):
        print_sql = kwargs.get('print_sql', False)        
        
        for entity in self.parent_resolver.resolve(session):
            query = self.create_query(session, entity)                            
            if print_sql:
                yield str(query)
                
            else: 
                for inst in query:
                    yield inst
    
class ElementNameResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    FIRST_CHAR = "[^\[/\s,\'\<\{]"
    MIDDLE_CHARS = "[^/\s,\']*"
    LAST_CHAR = "[^\]/\s,\'\>\}]?"    
    
    REGEX = re.compile("^(%s)%s(%s%s%s)$" % 
        (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR, FIRST_CHAR, MIDDLE_CHARS, LAST_CHAR)
    )
    
    @property
    def instance_name(self):
        return self.instance_spec 

    def resolve(self, session, **kwargs):
        for entity in self.parent_resolver.resolve(session, **kwargs):        
            element = session.query(entity).filter_by(instance_name=self.instance_name).limit(1).first()
            if element is None:
                raise UnknownElementError(self.spec)
            else:
                yield element
    
    def set(self, session, value):
        pass


class ElementIdResovlver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    REGEX = re.compile("^(%s)%s\{(\d+)\}$" % (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR)) 
        
    def instance_id(self):
        return self.instance_spec 
    
    
class ElementFormIdResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    REGEX = re.compile("^(%s)%s\<(\d+)\>$" % (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR))

    def instance_form_id(self):
        return self.instance_spec 
    
    
    
    
class AttributeSpecResolver(Resolver):
    def __init__(self, parser, spec):
        Resolver.__init__(self, parser, spec)
        
        if self.spec.count(Resolver.ATTRIBUTE_PATH_SEPARATOR) < 1:
            raise SpecMatchError("Spec: too few separators: %s" % Resolver.ATTRIBUTE_PATH_SEPARATOR)  

        (parent_spec, prop_name) = self.spec.rsplit(Resolver.ATTRIBUTE_PATH_SEPARATOR, 1)                
        self.parent_resolver = parser.parse(parent_spec)        
        self.property_name = prop_name
        
        for entity in self.parent_resolver.get_entity():
            if not entity.has_sa_property(prop_name):
                raise InvalidAttributeError("Entity '%s' does not have property: %s"
                    % (entity, prop_name))
    
            if isinstance(entity.get_sa_property(prop_name), sa_props.ColumnProperty) \
                and self.resolve_instance:
                raise InvalidObjectSpecError("Property '%s.%s' is an attribute, not a relation. \
                                        Cannot resolve instance. (perhaps remove trailing '/' ?)" % 
                                        (entity, prop_name))

        
        
    def get_entity(self):
        for entity in self.parent_resolver.get_entity():            
            self.sa_property = entity.get_sa_property(self.property_name)
        
            if isinstance(self.sa_property, sa_props.ColumnProperty):
                yield None
            
            elif isinstance(self.sa_property, sa_props.RelationProperty):
                if isinstance(self.sa_property.argument, sa_orm.Mapper):            
                    target_cls = self.sa_property.argument.class_
                else:
                    target_cls = self.sa_property.argument

                yield target_cls
            
            else:
                yield None
        
    
    def resolve(self, session, **kwargs):
        for element in self.parent_resolver.resolve(session, **kwargs):
            yield element.attribute(self.property_name)
        
    def set(self, session, value):
        for element in self.parent_resolver.resolve(session, **kwargs):
            element.attribute(self.property_name).set(value)
            
 
class ObjectSpecParser(object):

    def __init__(self, entity_set):
        self.entity_set = entity_set
        
    
    RESOLVERS = (
        EntityNameResolver,
        ElementNameResolver,
        ElementQueryResolver,
        ElementIdResovlver,
        ElementFormIdResolver,
        AttributeSpecResolver
    )
    
    def parse(self, spec, expected=RESOLVERS):        
        
        if not isinstance(expected, (list, tuple, types.GeneratorType)):
            expected = (expected,)
        
        self.log.fine("Parse Spec: %s", spec)
        for resolver_class in self.RESOLVERS:
            try:                
                if resolver_class not in expected:
                    next
                
                self.log.fine("   Try: %s", resolver_class)
                resolver = resolver_class(self, spec)
                self.log.fine("   Found")
                return resolver
            except SpecMatchError, e:
                self.log.fine("   Not Found. Parse result: %s" % e.msg)
            
        raise InvalidObjectSpecError("Could not parse object specification: %s" % spec)
        
class_logger(ObjectSpecParser)       



