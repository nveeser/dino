from optparse import Option
import logging

import sqlalchemy.orm.properties as sa_props
import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types

from dino.config import load_config
from dino.cmd.command import AbstractCommandInterface, CommandMeta, with_session, with_connection
from dino.cmd.maincmd import MethodSubCommand, ClassSubCommand
from dino.cmd.exception import *
from dino.db import *


        

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Define Base/Root Command 
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class AdminCommand(ClassSubCommand):
    NAME = 'admin'
    USAGE = '<subcommand> [ <args> ]'
    GROUP = 'system'


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Root Class Based SubCommand
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class AdminSubCommand(AbstractCommandInterface):
    '''Base Class of all subcommands'''    
    NAME = None
    
    __metaclass__ = CommandMeta
    
    def __init__(self, db_config, cli=None):
        self.db_config = db_config
        self.cli=cli
    
    def execute(self):
        raise NotImplemented()

    def parse(self, args):
        (self.option, self.args) = self.parser.parse_args(args=args)

    def print_usage(self):
        print self.prog_name + " " + self.MAIN_COMMAND_NAME + " " + self.NAME + " " + self.USAGE
    
    def print_help(self):
        print "   ", self.__class__.__doc__
      
      
ClassSubCommand.set_subcommand(AdminCommand, AdminSubCommand) 
         
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Sub Commands
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        
class DropAllCommand(AdminSubCommand):
    '''drop all tables listed in the current metadata (entity_set)'''
    
    NAME = 'dropall'
    USAGE = ''
    
    @with_connection
    def execute(self, connection):
        """drop all tables listed in the current metadata (entity_set)"""
        
        self.db_config.assert_unprotected()
      
        self.log.info("DROP Tables")  
        self.db_config.drop_all()
     
class ClearSchemaCommand(AdminSubCommand):
    """drop all tables present in the schema"""
        
    NAME = 'clear_schema'
    USAGE = ''
       
    @with_connection
    def execute(self, connection):
        self.db_config.assert_unprotected()
         
        self.db_config.clear_schema()
    
        


class CreateAllCommand(AdminSubCommand):
    """create all tables listed"""   
    NAME = 'createall'
    USAGE = ''

    def execute(self):                
        self.log.info("CREATE Tables")
        self.db_config.create_all()
        

class TruncateCommand(AdminSubCommand):
    """truncate each table listed """
    NAME = 'truncate'
    USAGE = ''

    @with_connection
    def execute(self, connection): 
        
        self.db_config.assert_unprotected()    
        connection.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        self.log.info("Truncating Tables")
        for md in self.db_config.metadata_set:
            for t in self.db_config.metadata.tables:
                self.log.info("Truncate Table: " + t)
                connection.execute('TRUNCATE TABLE %s' % t)
        
        connection.execute("SET FOREIGN_KEY_CHECKS = 1")        
    
class SchemaDumpCommand(AdminSubCommand):
    """ Print full Schema DDL for model"""
    NAME = 'schema'
    USAGE = ''
    
    def execute(self):
        print self.db_config.dump_schema()

class ConfigDumpCommand(AdminSubCommand):
    NAME = 'config'
    USAGE = ''
    
    def execute(self):
        cfg = load_config()
        
        main_sections = ['db', 'logging', 'migrate', 'generate']
        for name in main_sections:
            if not cfg.has_section(name):
                self.log.warn("missing section: %s", name)
                continue
            self._dump_section(cfg, name)
            
        for name in cfg.sections(): 
            if name in main_sections:
                continue
            self._dump_section(cfg, name)
    
    def _dump_section(self, cfg, section_name):
        print "[%s]" % section_name
        for option in sorted(cfg.options(section_name)):
            print "%s: %s" % (option, cfg.get(section_name, option))
        print 
        
        
class CheckProtectedCommand(AdminSubCommand):
    """ Get/Set state of the 'protected' value in the Schema Info"""       
    NAME = 'protected'
    USAGE = '[ <newvalue> ]'

    @with_session
    def execute(self, session): 
        info = self.db_config.schema_info()
                
        if len(self.args) > 0:
            
            try:               
                x = eval(self.args[0]) 
                new_value = bool(x)
            except Exception, e:
                raise CommandArgumentError(self, "Could not parse '%s' (%s)" % (self.args[0], e))
                
                
            if new_value != info.protected:
                sess = self.db_config.session()
                
                sess.open_changeset()
                sess.add(info)
                info.protected = new_value
                cs = sess.submit_changeset()  

                sess.refresh(info)
                sess.expunge(info)
    
                sess.close()
                 
                print "ChangeSet: %s" % cs
                
                
        print info.protected
                
        
        
class UpdateNamesCommand(AdminSubCommand):        
    """ For all Elements in the model entity set, pull each instance and validate/update the instance_name column"""
    NAME = 'update_names'
    USAGE = ''
          
    @with_session    
    def execute(self, session):
 
        session.begin()
        
        for entity in session.entity_iterator():
            self.log.info("Processing: %s" % entity.__name__)
            
            for instance in session.query(entity).all():
                instance.update_name()
                                    
        desc = session.create_change_description()

        session.commit()

        for change in desc:
            self.log.info(str(change))

class UpdateSubnetsCommand(AdminSubCommand):
    '''Validate that all subnets have the most appropriate parent subnet assigned'''
    NAME = 'update_subnets'
    USAGE = ''
        
    @with_session
    def execute(self, session):        
        session.begin()
        for addr in session.query(IpAddress).all():            
            subnet = addr.query_subnet()
            if addr.subnet != subnet:
                self.log.info("Updating: %s", str(addr))
                addr.subnet = subnet
                
        if len(session.dirty) > 0:
            self.log.info("Flushing: %d" % len(session.dirty))
            session.commit()
        else:
            self.log.info("No Changes")
            
 
class DotCommand(AdminSubCommand):
    NAME = 'dot'
    USAGE = ""
    OPTIONS = ( 
        Option('-f', dest='outfile', default=None), 
    )

    
    HEADER = '''
digraph M {         
    fontsize = 8
    overlap=False
    node [
         fontsize = 8
         shape = "record"
    ]
    
    edge [
            fontsize = 8
            tailport = _
            headport = _
    ]
'''     
    
    def validate(self):
        pass
    
    @with_session
    def execute(self, session):
        if self.option.outfile:            
            f = open(self.option.outfile, 'w')
        else:
            f = sys.stdout
        
        
        f.write(self.HEADER)
        for entity in session.entity_iterator(revisioned=False):

            if session.is_changeset_entity(entity):
                continue

            label_text = self._create_label(entity)        
                            
            f.write("   " + entity.__name__ + " [\n")                            
            f.write("\tlabel = \"%s\"\n" % label_text)
            f.write("    ];\n") 
            
            for line in self._generate_relations(entity):
                f.write(line + "\n")        
        f.write("}\n")
 
 
        
    def _create_label(self, entity):
               
        props = list(entity.mapper.iterate_properties)
        col_props = set([ p for p in props if isinstance(p, sa_props.ColumnProperty) ])
        rel_props = set([ p for p in props if isinstance(p, sa_props.RelationProperty) ])
        
        relation_names = [ p.key for p in rel_props ]
        rel_id_props = set([ p for p in col_props 
                                if p.key.endswith("_id") and p.key[:-3] in relation_names ])

        readonly_props = set([ p for p in props
                if p.key in ('instance_name','id', 'revision', 'changeset') ])   


        # System Props
        sys_cols = [ "*%s: %s\l" % (col_prop.key, self._get_column_info(col_prop))
            for col_prop in col_props & readonly_props ]                           
        sys_rels = [ "<%s>*%s -\> %s\l" % (rel_prop.key, rel_prop.key, self._get_relation_name(rel_prop))            
            for rel_prop in rel_props & readonly_props ]    
        # Columns     
        col_labels = [ "%s: %s\l" % (col_prop.key, self._get_column_info(col_prop))
            for col_prop in col_props - rel_id_props - readonly_props ]        
        # Relations
        rel_labels = [ "<%s>%s -\> %s\l" % (rel_prop.key, rel_prop.key, self._get_relation_name(rel_prop)) 
            for rel_prop in rel_props - readonly_props]        


        flag_text = self._create_flag_text(entity) 
        prop_text = "|".join(sys_cols + sys_rels + col_labels + rel_labels)        
        return "{ <entity> %s  %s | %s }" % (entity.__name__, flag_text, prop_text)
            


    def _create_flag_text(self, entity):
        # Flags
        flags = []
        if issubclass(entity, Element):
            flags.append("E")        
        if issubclass(entity, ResourceElement):
            flags.append("RS")        
        if issubclass(entity, Element) and entity.has_revision_entity():
            flags.append("RV")
        
        if len(flags) > 0:
            return "  (%s)" % ",".join(flags)
        else:
            flag_text = ""
            
    def _get_column_info(self, col_prop):
        col_type = col_prop.columns[0].type
        if isinstance(col_type, sa_types.String):
            return "%s(%s)" % (col_type.__class__.__name__, col_type.length)
        else:
            return str(col_type)
            
    def _get_relation_name(self, rel_prop, list_info=True):
        if isinstance(rel_prop.argument, sa_orm.Mapper):            
            target_cls = rel_prop.argument.class_
        else:
            target_cls = rel_prop.argument
        
        if not list_info:
            return target_cls.__name__
            
        if rel_prop.uselist:
            return "[ " + target_cls.__name__ + " ]"
        else:
            return "( " + target_cls.__name__ + " )"


        
    def _generate_relations(self, entity):
        for prop in entity.mapper.iterate_properties:
            if isinstance(prop, sa_props.RelationProperty):
                
                rel_name = self._get_relation_name(prop, list_info=False)
                if rel_name == "ChangeSet":
                    continue
                yield "%s:%s -> %s:entity;" % (entity.__name__, prop.key, rel_name)



class ListLoggersCommand(AdminSubCommand):
    ''' Throw and Exception: used for testing'''
    
    NAME = 'loggers'
    USAGE = ''

    def execute(self):
        
        log = logging.getLogger("dino")
        
        loggers = sorted(list(self._find_loggers()))

        for l in loggers:
            print l.name
    
    def _find_loggers(self):
        for l in logging.Logger.manager.loggerDict.values(): 
            if isinstance(l, logging.Logger):
                if l.name.startswith("dino"):
                    yield l
                

class ErrorCommand(AdminSubCommand):
    ''' Throw and Exception: used for testing'''
    
    NAME = 'error'
    USAGE = ''

    def execute(self):
        self.a()
        
    def a(self):
        try:
            self.b()
        except Exception, e:
            raise CommandExecutionError(self, "Hello")
        
    def b(self):
        try:
            self.c()
        except ModelError, e:
            raise ElementException("Wrapped: %s" % str(e))
        
    def c(self):
        raise ModelError("Test error")
        
        
        
class ExportCommand(AdminSubCommand):
    ''' Form dump of all Entities in the Database'''
    NAME = None #'export'
    USAGE = '[ -d <directory> ] [ <EntityName> | <ElementName> ] '
    OPTIONS = ( 
        Option('-d', dest='outdir', default=None), 
        )

    def validate(self):        
        pass
        
    @with_session
    def execute(self, session):        
        if self.option.outdir:
            if not os.path.isdir(self.option.outdir):
                raise CommandArgumentError(self, "Path is not directory: %s" % self.option.outdir)
        
            outdir = os.path.abspath(self.option.outdir)
        else:
            outdir = os.path.abspath(os.getcwd())
            
        if len(self.args) > 0:
            onames = [ ObjectSpec.parse(arg, expected=ElementName) for arg in args ]
            
            element_classes = [ session.resolve_entity(oname.entity_name) for oname in onames if oname.instance_name is None ]
            elements = [ session.find_element(oname) for onames in oname if oname.instance_name is not None ]  
                                                       
        else:
            element_classes = list(self.db_config.entity_set)
            elements = []
        
        for element_class in element_classes:
            if issubclass(element_class, Element):
                if element_class.is_revision_entity():
                    continue
                               
            for element in session.query(element_class).all():
                self._write_instance(outdir, element)
    
        for element in elements:
            self._write_instance(outdir, element)
            
            
    def _write_instance(self, dir, element):
        print str(element)
        