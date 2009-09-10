import logging
import types     
import re
import yaml

import sqlalchemy.orm.properties as sa_props   
import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types

from dino.config import class_logger
from objectspec import *
from objectresolver import *
from exception import * 
from element import Element, ResourceElement

__all__ = [ 'MultiElementFormProcessor' ]

class ElementFormProcessor(object):
    '''
    Generate a text form for its element, and/or update that element based on the same form. 
    '''
            
    @classmethod
    def create(cls, session, **kwargs): 
        return MultiElementFormProcessor(session, **kwargs)
        

    def __init__(self, session, show_headers=True, show_type_info=False, 
                show_read_only=False, allow_create=False):        
        self.session = session
                
        self.show_headers = show_headers
        self.show_type_info = show_type_info
        self.show_read_only = show_read_only
    
        self.allow_create = allow_create
    
    def _quote_element_names(self, formstr):
        #import pdb;pdb.set_trace()
        for entity in self.session.entity_iterator():
            formstr = entity.element_name_regex().sub(lambda x: "\'%s\'" % x.group(1), formstr)            
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

    
class_logger(ElementFormProcessor)


class MultiElementFormProcessor(ElementFormProcessor):    

    def to_form(self, arg):
        form = ElementForm()                
        
        if isinstance(arg, Element):
            self._element_to_form(arg, form)
        
        elif isinstance(arg, (list, tuple, types.GeneratorType)):
            for instance in arg:                
                form.start_element()
                self._element_to_form(instance, form)
                #form.end_element()
                
        else:
            raise RuntimeError("to_form takes list or Element: %s" % type(arg))
            
        return str(form)
 

    def _element_to_form(self, instance, form):  
         
        props = list(instance.mapper.iterate_properties)
        col_attrs = set([ p.key for p in props if isinstance(p, sa_props.ColumnProperty) ])
        rel_attrs = set([ p.key for p in props if isinstance(p, sa_props.RelationProperty) ])

        readonly_attrs = set(('instance_name','id', 'revision', 'changeset'))


        if self.show_headers:
            form += ElementForm.SYSTEM_HEADING         
            form += ('element_name', instance.element_name )  
        else:
            form += ElementForm.HIGHLIGHT  
            form += ('element_name', instance.element_name )  
            form += ElementForm.HIGHLIGHT  
        
        if self.show_read_only:
            form += ('-id', instance.id)           
            if instance.has_revision_entity():                    
                form += ('-changeset', instance.changeset)   
                form += ('-revision', instance.revision)   
        
        
        if self.show_headers:
            form += ElementForm.ATTRIBUTES_HEADING  
                         
        # list of attributes which have relation counterparts (changeset_id -> changeset)        
        rel_id_attrs = set([ n for n in col_attrs if n.endswith("_id") and n[:-3] in rel_attrs ])
    
        if self.show_type_info:
            for name in col_attrs - (readonly_attrs | rel_id_attrs):
                form += self._get_type_info(instance, name)              
            form += "\n"
            
        for name in col_attrs - (readonly_attrs | rel_id_attrs):             
            form += (name, getattr(instance, name))
                        
        if self.show_headers:
            form += ElementForm.RELATIONS_HEADING  
                
        if self.show_type_info:      
            for name in rel_attrs - readonly_attrs:
                form += self._get_type_info(instance, name)
            form += "\n"
            
        for name in rel_attrs - readonly_attrs:    
            form += (name, getattr(instance, name))            

        
        return form
        
    def process(self, form):
        #print "-------FORM--------"        
        #print form
        #print "-------FORM--------"        
        tuple_list = list(self._parse_form_elements(form))
         
        for (resolver, form_dict) in tuple_list:
            if isinstance(resolver, (ElementFormIdResolver, ElementNameResolver)):    
               resolver.create_entity(self.session)
       
        is_modified = False
        for (resolver, form_dict) in tuple_list:          
            is_modified |= self._update_resolver_elements(resolver, form_dict)
                    
        return is_modified 


    def _parse_form_elements(self, form):
        ''' Parse the form and return the Element specified by element_name, and 
        the dictionary of values to use to update the element.
        '''        
        form = self._quote_element_names(form)
        
        for value_dict in yaml.load_all(form):            
            if value_dict is None:
                continue
                
            try:
                if self.allow_create:
                    expected = (ElementNameResolver, ElementIdResolver, ElementFormIdResolver)
                else:
                    expected = (ElementNameResolver, ElementIdResolver)
                
                resolver = self.session.spec_parser.parse(value_dict['element_name'], expected=expected)
                yield (resolver, value_dict)
    
            except KeyError, e:
                raise ElementFormException("Form missing field: element_name")
 
 
    def _update_resolver_elements(self, resolver, form_dict):
        is_modified = False

        # Remove system properties from the form dictionary.
        for key in ('id', 'element_name', 'instance_name', 'revision', 'changeset_id', ):
            form_dict.pop(key, None)
            
        # Remove keys marked as 'read-only'
        for key in form_dict.keys():
            if key.startswith('-'):
                form_dict.pop(key, None)
        
        for element in resolver.resolve(self.session): 
            if element not in self.session:
                self.session.add(element)
                                                        
            for (name, value) in form_dict.iteritems():                    
                element.element_property(name).set(form_dict[name])    
            
            is_modified |= self.session.is_modified(element)
        
        return is_modified


class PropertySetFormProcessor(ElementFormProcessor):
    
    def _prop_set_to_form(self, instance, form):
        pass
    
    def to_form(self, instance):
                
        assert isinstance(instance, PropertySet)
        form = ElementForm()                
            
        self._prop_set_to_form(instance, form)
            
        return str(form)






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
    
    def start_element(self):
        if self.buf != "":
            self.buf += "---\n"
    
    def end_element(self):
        self.buf += "...\n"
        
    def __str__(self):
        return self.buf

class_logger(ElementForm)



