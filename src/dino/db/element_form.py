import logging
import types     
import re
import datetime
import yaml

import sqlalchemy.orm.properties as sa_props   
import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types

from dino.config import class_logger
from objectspec import *
from exception import * 
from element import Element, ResourceElement


class ElementFormProcessor(object):
    '''
    Generate a text form for its element, and/or update that element based on the same form. 
    '''
            
    @classmethod
    def create(cls, session, **kwargs): 
        return MultiElementFormProcessor(session, **kwargs)
        

    def __init__(self, session, show_headers=True, show_type_info=False, show_read_only=False):        
        self.session = session
                
        self.show_headers = show_headers
        self.show_type_info = show_type_info
        self.show_read_only = show_read_only
    
    
    def _quote_element_names(self, formstr):
        for e in self.session.entity_iterator():
            formstr = e.element_name_re().sub(lambda x: "\'%s\'" % x.group(1), formstr)
        return formstr

    def _get_type_info(self, instance, name):
        property = instance.get_sa_property(name)
        
        if isinstance(property, sa_props.ColumnProperty):
            return "# %s: %s\n" %  (str(property), property.columns[0].type)
            
        if isinstance(property, sa_props.RelationProperty):
            if isinstance(sa_property.argument, sa_orm.Mapper):            
                target_cls = sa_property.argument.class_
            else:
                target_cls = sa_property.argument
            
            if property.uselist:
                prop_type = "[ " + target_cls.__name__ + ", ... ]"
            else:
                prop_type = target_cls.__name__
                
            return "# %s: %s\n" %  (str(property), prop_type)  



    class ElementForm(object):
        
        HIGHLIGHT = '''\
#############################################
'''        
        SYSTEM_HEADING = '''\
#############################################
# System Attributes (Read-Only)                     
#                 
'''
        ATTRIBUTES_HEADING = '''\

#############################################
# Attributes               
#
'''
        RELATIONS_HEADING = '''\

#############################################
# Relationships  
#
'''
        ELEMENT_HEADING = '''\
#############################################
# %(element_name)s
#
'''
        INDENT = "   "
        
        def __init__(self):
            
            self.buf = ""
            
        def __iadd__(self, x):
            if isinstance(x, basestring):      
                self.buf += x
            
            elif isinstance(x, list):
                for v in x:
                    assert isinstance(v, tuple), "Must be a list of tuples"
                    self += v 
            
            elif isinstance(x, dict):            
                for (name, value) in x.iteritems():
                    self += (name, value)
    
            elif isinstance(x, tuple):
                assert len(x) == 2, "Tuple must be of length 2"
                (name, value) = x    
                self._append_key_value(name, value)
                                  
            else: 
                raise Exception("Bad form arument: must be (str, tuple, dict): %s" % type(x))
    
            return self
        
        def _append_key_value(self, name, value):
            if isinstance(value, (list, set, types.GeneratorType)):
                if len(value) > 3:
                    self._append_block_list(name, value)
                else:
                    self._append_flow_list(name, value)
                                    
            elif isinstance(value, basestring): 
                if value.find("\n") != -1:
                    self._append_block_scalar(name, value)
                                    
                else:
                    self._append_flow_scalar(name, value)
                    
            else:
                # Just make a string out of it
                self._append_flow_scalar(name, str(value) )
                

        def _append_flow_list(self, name, values):
            str_values = sorted([ str(x) for x in values ])    
            str_value = "[ " + ", ".join(str_values) + " ]"
            self._append_key_value(name, str_value)
            
        def _append_block_list(self, name, values):
            assert isinstance(values, (list, set, types.GeneratorType)), "TYPE: %s" % type(values)
            self.buf += "%s: \n" % name
            for value in sorted(values):
                self.buf += self.INDENT + "- %s\n" % value
        
        def _append_flow_scalar(self, name, value):
            self.buf += "%s: %s\n" % (name, str(value))
            
        def _append_block_scalar(self, name, value):
            self.buf += "%s: |\n" % (name)
            for line in value.split("\n"):
                self.buf += self.INDENT + "%s\n" % line
        
        def start_instance(self):
            if self.buf != "":
                self.buf += "---\n"
        
        def end_instance(self):
            self.buf += "...\n"
            
        def __str__(self):
            return self.buf

    class_logger(ElementForm)
    
class_logger(ElementFormProcessor)


class MultiElementFormProcessor(ElementFormProcessor):    

    def to_form(self, arg):
        form = self.ElementForm()                
        
        if isinstance(arg, Element):
            self._instance_to_form(arg, form)
        
        elif isinstance(arg, (list, types.GeneratorType)):
            for instance in arg:                
                form.start_instance()
                self._instance_to_form(instance, form)
                #form.end_instance()
                
        else:
            raise RuntimeError("to_form takes list or Element: %s" % type(arg))
            
        return str(form)


    def _instance_to_form(self, instance, form):  
         
        props = list(instance.mapper.iterate_properties)
        col_attrs = set([ p.key for p in props if isinstance(p, sa_props.ColumnProperty) ])
        rel_attrs = set([ p.key for p in props if isinstance(p, sa_props.RelationProperty) ])

        readonly_attrs = set(('instance_name','id', 'revision', 'changeset'))


        if self.show_headers:
            form += self.ElementForm.SYSTEM_HEADING         
            form += ('element_name', instance.element_name )  
        else:
            form += self.ElementForm.HIGHLIGHT  
            form += ('element_name', instance.element_name )  
            form += self.ElementForm.HIGHLIGHT  
        
        if self.show_read_only:
            form += ('-id', instance.id)           
            if instance.has_revision_entity():                    
                form += ('-changeset', instance.changeset)   
                form += ('-revision', instance.revision)   
        
        
        if self.show_headers:
            form += self.ElementForm.ATTRIBUTES_HEADING  
                         
        # list of attributes which have relation counterparts (changeset_id -> changeset)        
        rel_id_attrs = set([ n for n in col_attrs if n.endswith("_id") and n[:-3] in rel_attrs ])
    
        if self.show_type_info:
            for name in col_attrs - (readonly_attrs | rel_id_attrs):
                form += self._get_type_info(instance, name)              
            form += "\n"
            
        for name in col_attrs - (readonly_attrs | rel_id_attrs):             
            form += (name, getattr(instance, name))
                        
        if self.show_headers:
            form += self.ElementForm.RELATIONS_HEADING  
                
        if self.show_type_info:      
            for name in rel_attrs - readonly_attrs:
                form += self._get_type_info(instance, name)
            form += "\n"
            
        for name in rel_attrs - readonly_attrs:    
            form += (name, getattr(instance, name))            

        
        return form
        


    def _form_elements(self, form, expected=(ElementName, ElementId, ElementFormId)):        
        form = self._quote_element_names(form)
        
        for value_dict in yaml.load_all(form):
            try:
                element_spec = ObjectSpec.parse(value_dict['element_name'], expected=expected)
                yield (element_spec, value_dict)
                
            except KeyError, e:
                raise ElementFormException("Form missing field: element_name")
                
                
class MultiCreateFormProcessor(MultiElementFormProcessor):
            
    def __init__(self, *args, **kwargs):
        MultiElementFormProcessor.__init__(self, *args, **kwargs)
        self.element_cache = {}
        
        
    def create_empty_element(self, element_spec):
        self.log.fine("Creating in instance cache: %s", element_spec.object_name)
        assert isinstance(element_spec, (ElementName, ElementId, ElementFormId)), "element_spec wrong type: %s" % type(element_spec)  
                   
        element = self.session.resolve_entity(element_spec.entity_name).create_empty()
        self.element_cache[element_spec.object_name] = element
    
        self.session.add(element)


    def process(self, form, force_rollback=False):        
        tuple_list = list(self._form_elements(form))
         
        for (ename, form_dict) in tuple_list:            
            self.create_empty_element(ename)
       
        is_modified = False
        for (ename, form_dict) in tuple_list:
             
            if ename.object_name in self.element_cache:
                element = self.element_cache[ename.object_name]
            else:
                element = self.session.resolve_element_spec(ename)
                                
            ElementUpdater(element, element_cache=self.element_cache).update_dict(form_dict)
                        
            is_modified = is_modified or self.session.is_modified(element)
            
        return is_modified 
        
        
class MultiUpdateFormProcessor(MultiElementFormProcessor):
            
    def process(self, form):        
        form = self._quote_element_names(form)
        form_dict_list = yaml.load_all(form)

        is_modified = False
        for (ename, form_dict) in self._form_elements(form, expected=ElementName): 
            element = self.session.resolve_element_spec(ename)                

            ElementUpdater(element).update_dict(form_dict)                     

            is_modified = is_modified or self.session.is_modified(element)
                    
        return is_modified



    
class ElementUpdater(object):

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
    

    def __init__(self, element, element_cache={}):        
        self.element = element 
        self.element_cache = element_cache

    def update_dict(self, form_dict):
        '''
        Update the instance using the dictionary.
        map keys are PropertyNames on the mapped class, 
        map values are values or element names (or lists of element names ) of relations  
        '''                
        # Remove system properties from the form dictionary.
        for key in ('id', 'element_name', 'instance_name', 'revision', 'changeset_id', ):
            form_dict.pop(key, None)
            
        # Remove keys marked as 'read-only'
        for key in form_dict.keys():
            if key.startswith('-'):
                form_dict.pop(key, None)

        #self.log.finer("Update: %s" % instance.element_name)
        
        for (name, value) in form_dict.iteritems():
            if not self.element.mapper.has_property(name):
                raise InvalidFormAttributeNameError("Invalid Element Attribute: %s.%s" % (self.element.entity_name, name))
            
            sa_property = self.element.mapper.get_property(name)
                        
            self.log.finer("\t %s:%s" % (name, form_dict[name]))
            
            try:
                # Column Properties
                if isinstance(sa_property, sa_props.ColumnProperty):                                                                
                    self.update_column(name, form_dict[name])
    
                # Relation Properties
                elif isinstance(sa_property, sa_props.RelationProperty):
                    self.update_relation(name, form_dict[name])
    
                else:
                    raise UnknownFormPropertyTypeError("Unknown SqlAlchemy Property type for key %s.%s (%s): %s" 
                            % (self.element.entity_name, name, type(sa_property) ))
                            
            except TypeError, e:
                raise FormTypeError(self.element, name, value)
                
        
    def update_column(self, name, value): 
        sa_property = self.element.mapper.get_property(name)
        assert isinstance(sa_property, sa_props.ColumnProperty)
        
        coltype = sa_property.columns[0].type  
        
        if value is None:
            value = ""
                                                                     
        elif value == 'None':
            value = None
            
        elif type(coltype) in self.PARSER_MAP:
                value_type = self.PARSER_MAP[type(coltype)]
                value = value_type(value)
                  
        self.log.finer("\t   %s => %s" % (sa_property, value))
        setattr(self.element, name, value)
        
        
    def update_relation(self, name, value):
        sa_property = self.element.mapper.get_property(name)        
        assert isinstance(sa_property, sa_props.RelationProperty)
        
        # Find the target 'Entity' class of this relation  (ie Host.interfaces -> target_cls = Interface )
        if isinstance(sa_property.argument, sa_orm.Mapper):            
            target_cls = sa_property.argument.class_
        else:
            target_cls = sa_property.argument
        
        # Single Reference                                  
        if not sa_property.uselist:  
            assert not isinstance(value, list), "Value cannot be a list for this relation"
            if value == "None" or value is None:                        
                target_element = None
            else:            
                target_element = self._resolve_element_name(value, target_cls, self.element)
                assert isinstance(target_element, target_cls), "Object of wrong type: %s : %s" % (target_element.__class__, target_cls)                        
                
            self.log.finer("\t   %s: %s" % (sa_property, target_element))                            
            setattr(self.element, name, target_element)
        
        # List of References
        else: 
            assert isinstance(value, list), "Value must be a list for this relation"
                        
            current_collection = getattr(self.element, name)
            
            form_collection = [ self._resolve_element_name(element_name, target_cls, self.element) 
                                    for element_name in value ]
            
            for element in form_collection:                                                                                                     
                assert isinstance(element, target_cls), "Bad Relation Class: %s isn't %s" % (element.__class__, target_cls)                    
            
            # Remove deleted relations 
            for element in current_collection:
                if element not in form_collection:
                    self.log.finer("\t  %s + %s" % (sa_property, element))
                    current_collection.remove(element)     
            
            # Add missing relations
            for element in form_collection:                        
                if element not in current_collection:
                    self.log.finer("\t  %s - %s" % (sa_property, element))
                    current_collection.append(element)
    
    
    def _resolve_element_name(self, element_name, target_cls=None, instance=None):
        ''' Turn the string, specified by element_name, into an Element Instance.
        
        - If the target_cls is specified, and its a ResourceElement, 
            try creating the Element instance from the element_name as a "Value" for the resource
                
        - Look for the instance name in the ElementForm element_cache
            (which is valid only in the context of the form)
        
        - Finally, look up the string as a ElementName in the session
            (using ElementSession.find_element() )
            
        '''
        
        session = sa_orm.object_session(self.element)
        
        # ResourceElement
        if target_cls is not None and not ElementSpec.is_spec(element_name):
            if issubclass(target_cls, ResourceElement):
                self.log.finer("Create Resource from value: %s" % element_name)  
                return target_cls.create_resource(session, element_name, self.element)
            else:
                self.log.error("element_name does not match ObjectSpec: %s", element_name) 
                
        # Temp ElementName in instance_cache
        self.log.finer("Resolve ElementName: %s", element_name)        
        if element_name in self.element_cache:
            self.log.finer("  Found object in instance_cache")
            return self.element_cache[element_name]
        
        
        # Perm ElementName in Session / DB    
        self.log.finer("  Resolve from DB: %s", element_name)
        return session.resolve_element_spec(element_name)


class_logger(ElementUpdater)


class PropertySetFormProcessor(ElementFormProcessor):
    
    def _prop_set_to_form(self, instance, form):
        pass
    
    def to_form(self, instance):
                
        assert isinstance(instance, PropertySet)
        form = self.ElementForm()                
            
        self._prop_set_to_form(instance, form)
            
        return str(form)

                        
#    def _update_instance(self, instance, form_dict):                
#        # Remove system properties from the form dictionary.
#        for key in ('id', 'element_name', 'instance_name', 'revision', 'changeset_id', ):
#            form_dict.pop(key, None)
#            
#        # Remove keys marked as 'read-only'
#        for key in form_dict.keys():
#            if key.startswith('-'):
#                form_dict.pop(key, None)
#
#        self.log.finer("Update: %s" % instance.element_name)
#        
#        for (name, value) in form_dict.iteritems():
#            if not instance.mapper.has_property(name):
#                raise InvalidFormAttributeNameError("Invalid Element Attribute: %s.%s" % (instance.entity_name, name))
#            
#            sa_property = instance.mapper.get_property(name)
#                        
#            self.log.finer("\t %s:%s" % (name, form_dict[name]))
#            
#            try:
#                # Column Properties
#                if isinstance(sa_property, sa_props.ColumnProperty):                                                                
#                    self._update_instance_column(instance, sa_property, name, form_dict[name])
#    
#                # Relation Properties
#                elif isinstance(sa_property, sa_props.RelationProperty):
#                    self._update_instance_relation(instance, sa_property, name, form_dict[name])
#    
#                else:
#                    raise UnknownFormPropertyTypeError("Unknown SqlAlchemy Property type for key %s.%s (%s): %s" 
#                            % (instance.entity_name, name, type(sa_property) ))
#                            
#            except TypeError, e:
#                raise FormTypeError(instance, name, value)
#                
#        return instance
#    
#    def _update_instance_column(self, instance, sa_property, name, value): 
#        coltype = sa_property.columns[0].type  
#        
#        if value is None:
#            value = ""                                                         
#        elif value == 'None':
#            value = None
#        else:            
#            if type(coltype) in self.PARSER_MAP:
#                value_type = self.PARSER_MAP[type(coltype)]
#                value = value_type(value)
#                  
#        self.log.finer("\t   %s => %s" % (sa_property, value))
#        setattr(instance, name, value)
#           
#
#    def _update_instance_relation(self, instance, sa_property, name, value):
#                
#        # Find the target 'Entity' class of this relation  (ie Host.interfaces -> target_cls = Interface )
#        if isinstance(sa_property.argument, sa_orm.Mapper):            
#            target_cls = sa_property.argument.class_
#        else:
#            target_cls = sa_property.argument
#        
#        # Single Reference                                  
#        if not sa_property.uselist:  
#            assert not isinstance(value, list), "Value cannot be a list for this relation"
#            if value == "None" or value is None:                        
#                rel_instance = None
#            else:            
#                rel_instance = self._resolve_element_name(value, target_cls, instance)
#                assert isinstance(rel_instance, target_cls), "Object of wrong type: %s : %s" % (rel_instance.__class__, target_cls)                        
#                
#            self.log.finer("\t   %s: %s" % (sa_property, rel_instance))                            
#            setattr(instance, name, rel_instance)
#        
#        # List of References
#        else: 
#            assert isinstance(value, list), "Value must be a list for this relation"
#                        
#            form_collection = [ self._resolve_element_name(element_name, target_cls, instance) 
#                                    for element_name in value ]
#            
#            for rel_instance in form_collection:                                                                                                     
#                assert isinstance(rel_instance, target_cls), "Bad Relation Class: %s isn't %s" % (rel_element.__class__, target_cls)                    
#            
#            current_collection = getattr(instance, name)
#            
#            # Remove deleted relations 
#            for rel_instance in current_collection:
#                if rel_instance not in form_collection:
#                    self.log.finer("\t  %s + %s" % (sa_property, rel_instance))
#                    current_collection.remove(rel_instance)     
#            
#            # Add missing relations
#            for rel_instance in form_collection:                        
#                if rel_instance not in current_collection:
#                    self.log.finer("\t  %s - %s" % (sa_property, rel_instance))
#                    current_collection.append(rel_instance)
#
#
#    
#    def _resolve_element_name(self, element_name, target_cls=None, instance=None):
#        ''' Turn the string, specified by element_name, into an Element Instance.
#        
#        - If the target_cls is specified, and its a ResourceElement, 
#            try creating the Element instance from the element_name as a "Value" for the resource
#                
#        - Look for the instance name in the ElementForm instance_cache
#            (which is valid only in the context of the form)
#        
#        - Finally, look up the string as a ElementName in the session
#            (using ElementSession.find_element() )
#            
#        '''
#        
#        # ResourceElement
#        if target_cls is not None and not ElementSpec.is_spec(element_name):
#            if issubclass(target_cls, ResourceElement):
#                self.log.finer("Create Resource from value: %s" % element_name)  
#                return target_cls.create_resource(self.session, element_name, instance)
#            else:
#                self.log.error("element_name does not match ObjectSpec: %s", element_name) 
#                
#        # Temp ElementName in instance_cache
#        self.log.finer("Resolve ElementName: %s", element_name)        
#        if element_name in self.instance_cache:
#            self.log.finer("  Found object in instance_cache")
#            return self.instance_cache[element_name]
#        
#        
#        # Perm ElementName in Session / DB    
#        self.log.finer("  Resolve from DB: %s", element_name)
#        return self.session.resolve_element_spec(element_name)
