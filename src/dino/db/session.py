import sqlalchemy.orm.session
import sqlalchemy.orm.properties as sa_props
from sqlalchemy.orm.attributes import instance_state, manager_of_class
import sqlalchemy.exc as sa_exc


from dino.config import class_logger

from exception import UnknownElementError, DatabaseError, ElementExistsError
import changeset
from objectspec import *
import element


from sqlalchemy.orm.identity import StrongInstanceDict
class MyStrongInstanceDict(StrongInstanceDict):
    '''This is to fix a supposed bug in the original implementation'''
    
    def remove(self, state):
        dict.pop(self, state.key)
        self._manage_removed_state(state)
        
class ElementSession(changeset.ChangeSetSession):
    
    def __init__(self, *args, **kwargs):
        self.entity_set = kwargs['entity_set'] 
        cache = kwargs.pop('element_name_cache', False)
        
        self.rename_elements = []
        
        self.element_cache = None
            
        kwargs['weak_identity_map'] = False
        changeset.ChangeSetSession.__init__(self, *args, **kwargs)
        self._identity_cls = MyStrongInstanceDict
        self.identity_map = self._identity_cls()
                 
        self.extensions.append(self.ElementSessionExtension())  
    
    def commit(self):
        while self.rename_elements:
            self.rename_elements.pop().update_name()
        
        try:   
            changeset.ChangeSetSession.commit(self)
        
        except sa_exc.DatabaseError, e:
            raise DatabaseError("Error during commit", e)
            
    
    def create_change_description(self):
        return ChangeDescription(self)    
        
    def resolve_entity(self, entity_name):
        '''Find Python Class of the specified name'''
        return self.entity_set.resolve(entity_name)     

    def entity_iterator(self, revisioned=False):
        for e in self.entity_set:
            if issubclass(e, element.Element):
                if revisioned or not e.is_revision_entity():
                    yield e
 
         
         
    def _get_element_spec(self, object_spec):
        if isinstance(object_spec, basestring):
            element_spec = ObjectSpec.parse(object_spec, expected=(ElementName, ElementId, AttributeName))
        
        elif isinstance(object_spec, (ElementName, ElementId, AttributeName)):
            element_spec = object_spec
            
        else:    
            raise RuntimeError("method _get_element_spec() takes a basestring | ElementName | ElementId | AttributeName: %s" % type(object_spec))
    
        if isinstance(object_spec, AttributeName):
            element_spec = object_spec.element_spec
        
        return element_spec 
        
    def resolve_element_spec(self, object_spec):
        ''' 
        Resolve the instance specified by the ObjectSpec object
        If not found, throw an exception 
        '''
        element_spec = self._get_element_spec(object_spec)
        
        self.log.fine("Resolve Instance: %s" % element_spec.object_name)
        
        if self.element_cache and element_spec.object_name in self.element_cache:
            self.log.fine("  Found in ElementCache")
            return self.element_cache[element_spec.object_name]   
        
        return element_spec.resolve(self).next()

                
    def find_element(self, object_spec):
        ''' Find the instance specified by the ObjectSpec ( ElementName | ElementId | AttributeName )
        If the element is not found, return None
        '''

        element_spec = self._get_element_spec(object_spec)
        
        self.log.fine("Find Instance: %s" % element_spec.object_name)
        
        if self.element_cache and element_spec.object_name in self.element_cache:
            self.log.fine("  Found in ElementCache")
            return self.element_cache[element_spec.object_name]  
        
        try:
            return element_spec.resolve(self).next()
            
        except UnknownElementError:
            return None
            

    def query_instances(self, object_spec):
        ''' Find All Instances specified by the ObjectSpec ( ElementQuery | AttributeQuery )'''
        
        if isinstance(object_spec, basestring):
            obj_query = ObjectSpec.parse(object_spec, expected=ElementQuery)
        elif isinstance(object_spec, ElementQuery):
            obj_query = object_spec
        else:
            raise RuntimeError("query_instances() takes a basestring | ElementName: %s" % type(object_spec))
        
        return obj_query.create_query(self).all()


    def cache_add(self, instance, info=""):
        if self.element_cache is None:
            return 
        
        self.log.info("CACHE START ADD: %s", instance.object_id)
        if instance.element_name not in self.element_cache:
            self.log.info("  Add to ElementCache (%s) %s" % (info, str(instance)))
            #self.element_cache[instance.element_name] = instance
            
        if instance.object_id not in self.element_cache: 
            self.log.info("  Add to ElementIdCache (%s) %s" % (info, str(instance)))                                         
            #self.element_cache[instance.object_id] = instance       

        self.log.info("CACHE END ADD: %s", instance.object_id)

    def cache_delete(self, instance, info=""):
        if self.element_cache is None:
            return 
        
        self.log.info("CACHE START DELETE: %s", instance.object_id)

        if instance.element_name in self.element_cache:
            del self.element_cache[instance.element_name]
            
        if instance.object_id in self.element_cache:
            del self.element_cache[instance.object_id]

        self.log.info("CACHE END DELETE: %s", instance.object_id)


    class ElementSessionExtension(sqlalchemy.orm.session.SessionExtension):             
        def before_flush(self, session, flush_context, instances):
            from dino.db.element import Element
            for element in session.new:
                if isinstance(element, Element):
                    if session.query(element.__class__).filter_by(instance_name=element.instance_name).count() > 0:
                        raise ElementExistsError("Element already exists: %s" % element.element_name)


class_logger(ElementSession)


class ChangeDescription(list):    
    def __init__(self, session):
        for element in session.new:
            if session.is_changeset(element):
                continue
            self.append(AddElement(element))
            
        for element in session.deleted:
            self.append(DeleteElement(element))
                        
        for element in session.dirty:    
            for attr in element.mapper.class_manager.attributes:  
                self._read_attr(element, attr)   
 
    def _read_attr(self, element, attr):
        (added, unchanged, deleted) = attr.get_history(element, passive=False)
        
        if isinstance( attr.property, sa_props.ColumnProperty) and added:
            self.append(UpdateColumn(element, attr.key, added[0]))
            
        elif isinstance( attr.property, sa_props.RelationProperty):
            if attr.property.uselist:
                for x in added:
                    self.append(UpdateRelationManyAdd(element, attr.key, x))
                for x in deleted:                            
                    self.append(UpdateRelationManyDelete(element, attr.key, x))
                                     
            elif added:
                self.append(UpdateRelationOne(element, attr.key, added[0]))

class Change(object):
    def __init__(self, element):
        self.element = element
        
        
class AddElement(Change):
    def __str__(self):
        return "Add: %s" % str(self.element)
    
class DeleteElement(Change):
    def __str__(self):
        return "Delete: %s" % str(self.element)
    
class UpdateElement(Change):
    def __init__(self, element, name, value):
        Change.__init__(self, element)
        self.attrname = name 
        self.value = value
               
class UpdateColumn(UpdateElement):        
    def __str__(self):
        return "Update: %s/%s: %s" % (self.element, self.attrname, self.value)
        
class UpdateRelation(UpdateElement):
    def __init__(self, obj, name, value):
        if isinstance(value, element.Element):
            value = value.element_name
        UpdateElement.__init__(self, obj, name, value)
        
class UpdateRelationOne(UpdateRelation):
    def __str__(self):
        return "Update: %s/%s: %s" % (self.element, self.attrname, self.value)

class UpdateRelationManyAdd(UpdateRelation):
    def __str__(self):
        return "Update: %s/%s: add %s" % (self.element, self.attrname, self.value)

class UpdateRelationManyDelete(UpdateRelation):
    def __str__(self):
        return "Update: %s/%s: del %s" % (self.element, self.attrname, self.value)

                    
            
