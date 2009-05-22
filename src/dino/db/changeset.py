
import logging
import gc
import datetime

from itertools import ifilter
from copy import copy
                
import sqlalchemy
import sqlalchemy.schema
from sqlalchemy import and_, or_, between
from sqlalchemy import func, types
from sqlalchemy import exceptions

import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany, OneToOne

import collection

__all__ = [ 'using_changeset' , 'using_revisions' ]

__session__ = elixir.session = None # Make sure the global session is unset to turn off Scoped Session
__entity_collection__ = elixir.EntityCollection()
__metadata__ = None  # No metadata should be pushed into the module metadata object



class ChangeSetSession(sqlalchemy.orm.session.Session):
    """ Special type of session which understands 'ChangeSet' sematics (begin and submit) 
    The ChangeSet
    """
    
    def __init__(self, *args, **kwargs):
        entity_set = kwargs.pop('entity_set')        
        sqlalchemy.orm.session.Session.__init__(self, *args, **kwargs)
        
        self.submitting = False
        self.changeset_ext = None
        self.last_changeset = None
        self.opened_changeset = None
        self._changeset_cls = None
        
        if entity_set.has_entity("ChangeSet"): 
            self._changeset_cls = entity_set.resolve("ChangeSet")       
            self.extensions.append(self.EXTENSION)
            
       
    NO_CHANGESET_ENTITY_MESSAGE = "Cannot call method on Session with no ChangeSet Entity in EntitySet"

    def is_changeset(self, inst):
        return self.using_changeset() and isinstance(inst, self._changeset_cls)
        
    def is_changeset_entity(self, class_):
        return self.using_changeset() and issubclass(class_, self._changeset_cls)
        
    def using_changeset(self):
        return self._changeset_cls is not None

    def rollback(self):
        sqlalchemy.orm.session.Session.rollback(self)
        self.open_changeset = None
        
    def commit(self):
        self.submitting = True                    
        
        sqlalchemy.orm.session.Session.flush(self)
        sqlalchemy.orm.session.Session.commit(self)
      
        if self.opened_changeset and self.opened_changeset.id:
            self.last_changeset =  self.opened_changeset    
            self.opened_changeset = None          
            self.refresh(self.last_changeset)
            self.expunge(self.last_changeset)
        
        self.submitting = False

    def open_changeset(self):
        assert self.using_changeset(), self.NO_CHANGESET_ENTITY_MESSAGE
        self.begin()
        self._assert_changeset()
        return self.opened_changeset

    def revert_changeset(self):
        assert self.using_changeset(), self.NO_CHANGESET_ENTITY_MESSAGE
        self.rollback()               
        return self.opened_changeset
        
    def submit_changeset(self):
        assert self.using_changeset(), self.NO_CHANGESET_ENTITY_MESSAGE
        self.commit()
        return self.last_changeset

    
    
    def _assert_changeset(self):
        if self.opened_changeset is None:
            self.opened_changeset = self._changeset_cls()
            self.add(self.opened_changeset)
            
        elif self.opened_changeset.id is not None:
            raise exceptions.InvalidRequestError("Cannot flush with ChangeSet that has already been committed")
        
        return self.opened_changeset
         
    
    class ChangeSetSessionExtension(sqlalchemy.orm.session.SessionExtension): 
        """ 
        Extension to a standard session which handles the automatic updating 
        of a changeset value on each "Revisioned" entity when it gets flushed. 
        """     

        def before_flush(self, session, flush_context, instances):
            assert isinstance(session, ChangeSetSession)
            
            for inst in session:            
                if not hasattr(inst, 'changeset'):
                    continue
                 
                if inst in session.deleted or inst in session.dirty or inst in session.new:
                    self.assert_submitting(session)                                                    
                    inst.changeset = session._assert_changeset()
                    
            if session.opened_changeset:
                session.opened_changeset.committed = datetime.datetime.utcnow()
            
        def after_attach(self, session, instance):
            assert isinstance(session, ChangeSetSession)
          
            if isinstance(instance, session._changeset_cls):
                return
                 
            if hasattr(instance, 'changeset'):                            
                instance.changeset = session._assert_changeset()
        
        def assert_submitting(self, session):
            if not session.submitting:
                raise RuntimeError("Don't flush outside of a changeset. It's confusing")
        
    EXTENSION = ChangeSetSessionExtension()          
    
    
class RevisionMapperExtension(sqlalchemy.orm.MapperExtension):
    """Extension to the mapping tool
        The mapping tool provides a mapping between an Entity Class, and the table 
        that it is related to.  Update the Entity instance -> update row in the table, etc
        This extension adds the functionality of also updating the (second) revision table
        also associated with the Entity when that entity is "Revisioned"  (i.e. use_changeset() ). 
    """
    
    def before_insert(self, mapper, connection, instance):
        instance.revision = 1
        return sqlalchemy.orm.EXT_CONTINUE

    def before_update(self, mapper, connection, instance):
        if instance.revision is None:
            raise RuntimeError("Update on collected object: %s %s" % (instance.__class__, instance.__dict__))
        instance.revision += 1
        return sqlalchemy.orm.EXT_CONTINUE

                
    def after_insert(self, mapper, connection, instance):
        self._add_revision(mapper, connection, instance)
        return sqlalchemy.orm.EXT_CONTINUE
 
    def after_update(self, mapper, connection, instance):
        self._invalidate_revision(mapper, connection, instance)     
        self._add_revision(mapper, connection, instance)
        return sqlalchemy.orm.EXT_CONTINUE

    def after_delete(self, mapper, connection, instance):
        self._invalidate_revision(mapper, connection, instance)     
        return sqlalchemy.orm.EXT_CONTINUE


    def _add_revision(self, mapper, connection, instance ):
        revision_dict = instance.get_revision_map()
        stmt = instance.Revision.table.insert( revision_dict )
        #import pdb; pdb.set_trace()
        connection.execute(stmt)

    def _invalidate_revision(self, mapper, connection, instance):
        revision_table = instance.Revision.table                
        
        stmt = revision_table.update() \
            .values({ 'changeset_invalid_id' : instance.changeset.id } ) \
            .where(and_( revision_table.c.head_id == instance.id, revision_table.c.changeset_invalid_id == None))
        connection.execute(stmt)

_revision_mapper_extension = RevisionMapperExtension()


def create_changeset_entity():
    """ Create a new ChangeSet Entity.
    Each entity collection should have its own ChangeSet Entity.
    We create it here.
    """
        
    class ChangeSet(elixir.Entity):
        elixir.using_options(tablename='changeset')
        elixir.using_table_options(mysql_engine='InnoDB')
        
        created = Field( types.DateTime, default=func.now())
        committed = Field( types.DateTime, default=None )
        author = Field( types.String(15) )
        comment = Field( types.Text )
        
        def __init__(self):
            import datetime
            self.created = datetime.datetime.now() # eval'ed in python when object is created.
            self.committed = None
        
        def is_open(self):
            return self._changeset.id is None
        
        def __cmp__(self, obj):
            if isinstance(obj, ChangeSet):
                return self.id - obj.id
            else:
                raise TypeError
        
        def __int__(self):
            if self.id is not None:
                return int(self.id)
            else:
                return 0
        
        def __str__(self):
            return str(int(self))
            
    return ChangeSet

class RevisionEntityBuilder(elixir.properties.EntityBuilder):
    """Elixir EntityBuilder that participates in the building of an Entity during 
    
    Create a Revision Entity that is related to its Head Entity, as well as 
    created a (second) Revision table that is related to the Revision Entity.
    
    A copy of each column in the Head Entity Table, is copied to the Table Revision Entity, 
    and any foreign keys are relaligned, or replaced.
    """

    def __init__(self, entity, ignore=[]):
        self.entity = entity
        self.add_mapper_extension(_revision_mapper_extension)

        ignore.extend(['id'])
        entity.__ignored_fields__ = ignore
     
        ManyToOne('ChangeSet', required=True).attach(self.entity, 'changeset')
        Field(types.Integer, nullable=False).attach(self.entity, "revision")

        self.entity.Revision = self._create_revision_class()

        
        if "ChangeSet" not in [ e.__name__ for e in self.entity._descriptor.collection ]:
            changeset_entity = create_changeset_entity()
            changeset_entity._descriptor.metadata = self.entity._descriptor.metadata
            changeset_entity.__module__ = self.entity.__module__
            self.entity._descriptor.collection.append(changeset_entity)
  
        
    def _create_revision_class(self):
        entity = self.entity

        def init(self):
            self._changeset_view = None
                
        name = entity.__name__ + 'Revision'
        # Re-Parent Revision Entity of this class to the RevisionEntity of parent
        # child(parent) and child.Revision(parent.Revision)
        bases = tuple([ hasattr(b, 'Revision') and b.Revision or b for b in entity.__bases__ ])
        
        if '__str__' in entity.__dict__:
            str_func = entity.__dict__['__str__'] 
        else:
            str_func = object.__str__
            
        dict_ = {
            '__name__' : name,
            '__module__' : entity.__module__,
            '__main_entity__' : entity,
            # Basic methods
            '__init__' : init,
            '__str__' : str_func,
            # New Fields
            'head' : ManyToOne(entity.__name__, 
                constraint_kwargs={ 'ondelete' : 'NO ACTION'}, 
                column_kwargs={ 'index' : True } ), 
            'changeset_invalid' : ManyToOne('ChangeSet'),            
        }        
        
        revision_entity = entity.__metaclass__(name, bases, dict_)
                
        revision_entity._descriptor.tablename = self.entity._descriptor.tablename + '_revision'
        revision_entity._descriptor.metadata = self.entity._descriptor.metadata
        revision_entity._descriptor.table_options = dict(self.entity._descriptor.table_options)
          
        
        # Move the entity from the module collection (changeset.__entity_collection__) to 
        # the main entity's collection.   
        revision_entity._descriptor.collection.remove(revision_entity)
        revision_entity._descriptor.collection = self.entity._descriptor.collection
        revision_entity._descriptor.collection.append(revision_entity)
        
        return revision_entity

        



    def after_table(self): 
        #print "Entity: ", self.entity.__name__
        
        head_desc = self.entity._descriptor
        rev_desc = self.entity.Revision._descriptor
        
#        if head_desc.polymorphic and head_desc.inheritance in ('single', 'multi') and \
#         head_desc.children and not head_desc.parent:
#                rev_desc.add_column(Column(head_desc.polymorphic, elixir.options.POLYMORPHIC_COL_TYPE))
        
                        
        for builder in self.entity._descriptor.builders:            
            if isinstance(builder, Field):                
                column = builder.column.copy()
                column.unique=False  # remove unique constraints per column, cannot be unique across versions
                self.entity.Revision.table.append_column(column)                            

            elif isinstance(builder,(ManyToOne, ManyToMany)):
                #print "    Relation: ", self.entity, builder
                
                # Create a new relation from the old one.                
                if hasattr(builder.target, "Revision"):
                    new_builder = self._copy_builder(builder, builder.target.Revision)                    
                else:
                    new_builder = self._copy_builder(builder, builder.target)
                
                # rename constraint to be unique
                constraint_name = "%s_%s_id_fk" % ( self.entity.Revision.table.name, builder.name.lower() )
                new_builder.constraint_kwargs['name'] = constraint_name
                
                # catch this builder up with what the other builders have already done.
                # See entity.py#setup_entities() and EntityDescriptor#setup_*
                new_builder.attach(self.entity.Revision, builder.name)
                new_builder.create_pk_cols()
                new_builder.create_non_pk_cols()

                # If relation builder points to a Revision'd Entity, look for the 
                # constraint and fix its ForeignKey to point to the head_id, not 
                # the row id of the related *_revision table.
                if hasattr(builder.target, "Revision"):
                    for c in self.entity.Revision.table.constraints:
                        if c.name == constraint_name:
                            for fk in c.elements:
                                if fk.column.name == 'id':
                                    fk.column = fk.column.table.c['head_id']
                                    c.use_alter = True # make sure these constraints come at the end

        
        # Remove All Unique Constraints on the Revision Table 
        # And Remove FK Constraints from Revision To Primary Table
        for c in set(self.entity.Revision.table.constraints):

            if isinstance(c, sqlalchemy.schema.UniqueConstraint):
                self.entity.Revision.table.constraints.remove(c)
            
            if isinstance(c, sqlalchemy.schema.ForeignKeyConstraint):
                for fk in c.elements:
                    if isinstance(fk, sqlalchemy.schema.ForeignKey):
                        if fk.column.table == self.entity.table:
                            c.elements.remove(fk)
                            
                if len(c.elements) == 0:
                    self.entity.Revision.table.constraints.remove(c)
                            

                    


    @staticmethod
    def _copy_builder(builder, target):
        builder_copy = builder.__class__(target, *builder.args, **builder.kwargs)                    
        for attr in [ 'colname', 'column_kwargs', 'field', 'constraint_kwargs']:
            if builder.__dict__.has_key(attr):
                builder_copy.__dict__[attr] = builder.__dict__[attr]
            
        return builder_copy
        
        
    def finalize(self):
        self.update_revision_relations()
        self.create_entity_methods()

    def update_revision_relations(self):
        """ For Revision entities with Foreign Keys, change the "Property" from an InstrumentedAttribute, 
        to a ChangeSet-aware query method. 
        Ex For HostRevision hostrev, hostrev.addresses should return list<AddressRevision> not list<Address>, 
        at the same changeset that the hostrev was queried at"""
        
        # !!! Compile the mapper first, so that all the attributes are set before we modify them
        # We don't want the mapper coming back and overriding these changes when the Entity is first used.
        self.entity.Revision.mapper.compile()

        for prop in self.entity._descriptor.builders:            
            if not isinstance(prop, elixir.relationships.Relationship): continue
        
            if hasattr(prop.target, 'Revision'):   
                target_entity = prop.target.Revision                  
                target_table = prop.target.Revision.table
                
                #print self.entity, "->", target_entity
                
                # Get the target_column and the local_column_name 
                #
                if isinstance(prop, (ManyToOne, ManyToMany)):
                    target_column = target_table.c.head_id
                    local_column_name = prop.foreign_key[0].name
                    
                elif isinstance(prop, (OneToOne, OneToMany)):
                    target_column_name = prop._inverse.foreign_key[0].name
                    target_column = target_table.c[target_column_name]
                    local_column_name = 'head_id'
                
                
                # Create the methods (two get methods for two types of relationships)
                # 
                def target_get_entity(self):
                    session = sqlalchemy.orm.object_session(self)
                    assert session is not None, "Instance has no session: Must have session to read relations"
                    query = session.query(target_entity).filter( 
                        and_( 
                            target_column == getattr(self,local_column_name),                     
                            target_table.c.changeset_id >= self._changeset_view,
                            between(self._changeset_view, target_table.c.changeset_id, target_table.c.changeset_invalid_id)
                        )
                    ) 
                
                    e = query.first()
                    e._changeset_view = self._changeset_view
                    return e
                    
                def target_get_collection(self):
                    session = sqlalchemy.orm.object_session(self)
                    assert session is not None, "Instance has no session: Must have session to read relations"
                    query = session.query(target_entity).filter( 
                        and_(    
                            target_column == getattr(self,local_column_name),                     
                            target_table.c.changeset_id >= self._changeset_view,
                            between(self._changeset_view, target_table.c.changeset_id, target_table.c.changeset_invalid_id)
                        )
                    ) 
                
                    list = query.all()
                    for e in list:
                        e._changeset_view = self._changeset_view
                    return list
                    
                def target_set(self):
                    raise InvalidRequestError("Revision Objects are Read-Only")


                #
                # Replace the InstrumentedAttribute with a property
                #
                #print "Replace: ", self.entity.Revision, "->", prop.name, prop.__class__
                if type(prop) in (ManyToMany, OneToMany):
                    setattr(self.entity.Revision, prop.name, property(target_get_collection, target_set))
                elif type(prop) in (ManyToOne, OneToOne):
                    setattr(self.entity.Revision, prop.name, property(target_get_entity, target_set))
                else:
                    raise RuntimeError("Unknow Elixir Property Type: %s" % type(prop))
                

    def create_entity_methods(self):
        """ Create extra version related methods on the Head entity"""

        def get_revision_map(self):
            dict = { 'head_id' : self.id } 
            for field in self.table.c.keys():                    
                if field in self.__class__.__ignored_fields__:
                    continue   
                value = getattr(self, field)
                dict[field] = value
            return dict



        def get_revision(self, revision):
            sess = sqlalchemy.orm.object_session(self)
            
            query = sess.query(self.Revision).filter( and_(
                    self.Revision.head_id == self.id, 
                    self.Revision.revision == revision
                    )).limit(1)
            rev = query.first()
            rev._changeset_view = rev.changeset_id
            return rev 
        

        def get_at_changeset(self, changeset):
            sess = sqlalchemy.orm.object_session(self)
            
            q = sess.query(self.Revision)
            q = q.filter(and_(
                    self.Revision.head == self, 
                    self.Revision.changeset_id >= changeset,
                    between(changeset, self.Revision.changeset_id, self.Revision.changeset_invalid_id)
                    )).limit(1)
                    
            r = q.first()
            if r:
                r._changeset_view = changeset
            return r
                    
        self.entity.get_revision = get_revision
        self.entity.get_at_changeset = get_at_changeset
        self.entity.get_revision_map = get_revision_map


using_changeset = elixir.statements.Statement(RevisionEntityBuilder)
using_revisions = elixir.statements.Statement(RevisionEntityBuilder)





