import re
import types

import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props
import sqlalchemy.orm


from dino import class_logger
from exception import *
import element



__all__ = [ 'ObjectSpecParser',
            'EntityNameResolver',
            'ElementNameResolver',
            'ElementQueryResolver',
            'ElementIdResolver',
            'ElementFormIdResolver',
            'PropertySpecResolver',
            ]


class SpecMatchError(ObjectSpecParserError):
    '''Error used by the parser to signal that a 
    resolver does not match the supplied string/spec'''
    def __init__(self, msg):
        self.msg = msg


class Resolver(object):
    ATTRIBUTE_PATH_SEPARATOR = '/'
    ELEMENT_NAME_SEPARATOR = ':'
    QUERY_CLAUSE_START = '['
    RESOLVE_INSTANCE_SUFFIX = ATTRIBUTE_PATH_SEPARATOR

    def __init__(self, parser, spec):
        self.parser = parser

        if spec.endswith(self.RESOLVE_INSTANCE_SUFFIX):
            self.resolve_instance = True
            self.spec = spec[:-1]
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
    RESOLVE_INSTANCE_SUFFIX = Resolver.ELEMENT_NAME_SEPARATOR

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
            raise InvalidObjectSpecError("Unknown entity: not found in parser entity_set: ", self.spec)


    def get_entity(self):
        if self.entity is element.Element:
            for e in self.parser.entity_set:
                if issubclass(e, element.Element) and not e.is_revision_entity():
                    yield e

        else:
            yield self.entity


    def resolve(self, session, **kwargs):
        for entity in self.get_entity():
            if self.resolve_instance:
                for element in session.query(entity).all():
                    yield str(element)
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


    @staticmethod
    def create_element_name_regex(name):
        '''
        Return a compiled RegEx object that will exactly match 
        a ElementName string for the EntityName specified by Name
        
        The Groups within the match object are  (eg Device/foo)
        
        1: The ElementName : 'Device:foo'   (remove any single quotes)
        2: The EntityName : 'Device'
        3: The InstanceName : 'foo' 
        '''
        return re.compile("[']*((%s):([^/\s,\']*))[']*" % name)

    def create_entity(self, session):
        for entity in self.get_entity():
            session.add_temp_element(entity, self.instance_spec)


class ElementNameResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    FIRST_CHAR = "[^\[/\s,\'\<\{]"
    MIDDLE_CHARS = "[^/\s,\']*"
    LAST_CHAR = "[^\]/\s,\'\>\}]?"

    REGEX = re.compile("^(%s)%s(%s%s%s)$" %
        (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR, FIRST_CHAR, MIDDLE_CHARS, LAST_CHAR)
    )

    @staticmethod
    def make_name(entity_name, instance_name):
        return "%s%s%s" % (entity_name, Resolver.ELEMENT_NAME_SEPARATOR, instance_name)



    @property
    def instance_name(self):
        return self.instance_spec

    def resolve(self, session, **kwargs):
        for entity in self.parent_resolver.resolve(session, **kwargs):
            # Look in the database first                  
            elmt = session.query(entity).filter_by(instance_name=self.instance_name).limit(1).first()

            if elmt is None:
                # look in the session temp set next
                elmt = session.get_temp_element(entity, self.instance_spec)

            if elmt is None:
                # Still can't find it then error
                raise UnknownElementError(self.spec)

            yield elmt

    def set(self, session, value):
        pass


class ElementIdResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    REGEX = re.compile("^(%s)%s\{(\d+)\}$" % (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR))

    def instance_id(self):
        return self.instance_spec

    @staticmethod
    def to_instance_id(id):
        return "{%d}" % int(id)

    @staticmethod
    def make_name(elmt):
        return "%s%s{%s}" % (elmt.entity_name, Resolver.ELEMENT_NAME_SEPARATOR, elmt.id)


    def resolve(self, session, **kwargs):
        for entity in self.parent_resolver.resolve(session, **kwargs):
            element = session.query(entity).filter_by(id=self.instance_id).limit(1).first()
            if element is None:
                raise UnknownElementError(self.spec)

            yield element


class ElementFormIdResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[\]%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    REGEX = re.compile("^(%s)%s\<(\d+)\>$" % (ENTITY_NAME, Resolver.ELEMENT_NAME_SEPARATOR))

    def instance_form_id(self):
        return self.instance_spec

    @staticmethod
    def to_form_id(id):
        return "<%d>" % id

    def resolve(self, session, **kwargs):
        for entity in self.parent_resolver.resolve(session, **kwargs):
            element = session.get_temp_element(entity, self.instance_spec)
            if element is None:
                raise UnknownElementError(self.spec)
            else:
                yield element



class ElementQueryResolver(BaseElementResolver):
    ENTITY_NAME = "[^\[%s]+" % Resolver.ELEMENT_NAME_SEPARATOR
    QUEUE_CLAUSE = "[^\]]*"
    REGEX = re.compile("^(%s)\[(%s)\]$" % (ENTITY_NAME, QUEUE_CLAUSE))

    def __init__(self, parser, spec):
        BaseElementResolver.__init__(self, parser, spec)
        self.query_clause = self.instance_spec

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

    def _get_attr_obj(self, class_, property_name):
        if not hasattr(class_, property_name):
            raise QueryClauseError(self, "Invalid PropertyName on Element: %s.%s" % (class_, property_name))
        return getattr(class_, property_name)


    def resolve(self, session, **kwargs):
        for entity in self.parent_resolver.resolve(session):
            query = self.create_query(session, entity)
            if self.parser.print_query:
                yield str(query)

            else:
                for element in query:
                    if self.resolve_instance:
                        yield element
                    else:
                        yield element.element_name


class PropertySpecResolver(Resolver):
    REGEX = re.compile("^(.*/)([^/\[]+)(?:\[(\d+)\])?")

    @staticmethod
    def make_name(entity_name, instance_name, property_name):
        return ElementNameResolver.make_name(entity_name, instance_name) + \
             Resolver.ATTRIBUTE_PATH_SEPARATOR + property_name

    def __init__(self, parser, spec):
        Resolver.__init__(self, parser, spec)

        m = self.REGEX.match(self.spec) # don't use spec
        if m == None:
            raise SpecMatchError("Does not match Regex")

        (parent_spec, prop_name, index) = m.groups()

        expected = (ElementNameResolver, ElementQueryResolver, ElementIdResolver, ElementFormIdResolver, PropertySpecResolver)
        self.parent_resolver = parser.parse(parent_spec, expected=expected)
        self.property_name = prop_name
        if index is not None:
            self.list_index = int(index)
        else:
            self.list_index = None

        for entity in self.parent_resolver.get_entity():
            if not entity.has_sa_property(prop_name):
                raise InvalidAttributeSpecError("Entity '%s' does not have property: %s"
                    % (entity, prop_name), self.spec)

            sa_prop = entity.get_sa_property(prop_name)
            if isinstance(sa_prop, sa_props.ColumnProperty) \
                and self.resolve_instance:
                raise InvalidObjectSpecError("Property '%s.%s' is an attribute, not a relation. \
                                        Cannot resolve instance. (perhaps remove trailing '/' ?)" %
                                        (entity, prop_name), self.spec)
            if self.list_index is not None:
                if not isinstance(sa_prop, sa_props.RelationProperty):
                    raise InvalidAttributeSpecError("Can only specify an index against a relation, not a column property", spec)

                if not sa_prop.uselist:
                    raise InvalidAttributeSpecError("Can only specify an index against a OneToMany and ManyToMany relation", spec)


    def get_entity(self):
        for entity in self.parent_resolver.get_entity():
            sa_property = entity.get_sa_property(self.property_name)

            if isinstance(sa_property, sa_props.ColumnProperty):
                yield None

            elif isinstance(sa_property, sa_props.RelationProperty):
                if isinstance(sa_property.argument, sa_orm.Mapper):
                    target_cls = sa_property.argument.class_
                else:
                    target_cls = sa_property.argument

                yield target_cls

            else:
                yield None


    def resolve(self, session, **kwargs):
        for elmnt in self.parent_resolver.resolve(session, **kwargs):
            element_property = elmnt.element_property(self.property_name)

            if element_property.is_attribute():
                yield element_property

            elif element_property.is_relation_to_one():
                if self.resolve_instance:
                    yield element_property.value()
                else:
                    yield element_property

            elif element_property.is_relation_to_many():
                if self.list_index is not None:
                    try:
                        elmt = element_property.value()[self.list_index]
                    except IndexError:
                        yield None

                    if self.resolve_instance:
                        yield elmt
                    else:
                        yield str(elmt)

                else:
                    if self.resolve_instance:
                        for elmt in element_property.value():
                            yield elmt

                    else:
                        yield element_property






    def set(self, session, value):
        for elmnt in self.parent_resolver.resolve(session, **kwargs):
            elmnt.element_property(self.property_name).set(value)


class ObjectSpecParser(object):
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
        
        ---Entity Specification---
        
        EntityName := <String> 
            Name of Entity Class (Device, Subnet, Site, etc)
        
        ---Element Specification---
        
        ElementName := <EntityName> / <InstanceName> 
            User-Readable name of Element
                
            InstanceName := Unique, Human readable name based on the data in the instance 


        ElementId := <EntityName> / <InstanceId> 
            Databse Id based name of Element 
             
            InstanceId := '{' num '}'  Unique Integer id based on the unique id column in the database

        
        ElementFormId := <EntityName> / <FormId>
            Temporary Form based name of Element
        
            FormId :=  '<' num '>' Unique Integer within a given form context.  


        ElementQuery := <EntityName> '[' <QuerySpec> ']'
         
        --- Query Info ---

        QuerySpec := <QueryClause>[';'<QueryClause>[ ... ] ]
        
        QueryClause := <JoinClause> | <JoinFilterClause> | <ObjectFilterClause>

            JoinClause := <ElementName>  
    
            JoinFilterClause := <ElementName>.<PropertyName>=<value> 
    
            ObjectFilterClause := <PropertyName>=<value> 
        

        ---PropertySpec---

        PropertySpec := { <ElementName> | <ElementId> } / { <RelationPath> | <ColumnName> } 
        
        RelationPath := <RelationName> [ { / <RelationPath> ... | <ColumnName> } ]  

            
        
        -- Examples --

        EntityName
            Device
            Subnet

        ElementName:
            Device:001EC9437ABF
            Site:sjc1
        
        ElementId:
            Device:{12}
            Site:{304}
            
        ElementFormId:
            Device:<2>
            Port:<1>
            
        ElementQuery
            Device[hw_class=server]   # ObjectFilterClause
            Host[device.hw_class=server]  # JoinFilterClause
            Host[device;chassis.name=unknown]  # JoinClause + JoinFilterClause

        PropertySpec
            Device:001EC9437ABF/notes
            Host:hostname.ops.site/device/rack


     '''


    def __init__(self, entity_set, **kwargs):
        self.entity_set = entity_set
        self.print_query = kwargs.get('print_query', False)
        self.show_name = kwargs.get('show_name', False)

    RESOLVERS = (
        EntityNameResolver,
        ElementNameResolver,
        ElementQueryResolver,
        ElementIdResolver,
        ElementFormIdResolver,
        PropertySpecResolver
    )

    def _parse(self, spec, expected):
        if not isinstance(expected, (list, tuple, types.GeneratorType)):
            expected = (expected,)

        self.log.fine("Parse Spec: %s", spec)
        for resolver_class in self.RESOLVERS:
            try:
                if resolver_class not in expected:
                    continue

                self.log.fine("   Try: %s", resolver_class)
                return resolver_class(self, spec)

            except SpecMatchError, e:
                self.log.fine("   Not Found. Parse result: %s" % e.msg)

        return None

    def is_spec(self, spec, expected=RESOLVERS):
        return self._parse(spec, expected) is not None

    def parse(self, spec, expected=RESOLVERS):
        resolver = self._parse(spec, expected)

        if resolver is not None:
            self.log.fine("Found")
            return resolver

        else:
            raise InvalidObjectSpecError("Could not find resolver for spec", spec)

class_logger(ObjectSpecParser)



