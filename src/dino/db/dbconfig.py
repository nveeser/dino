import logging
import re

import sqlalchemy
from sqlalchemy import engine

from dino.config import class_logger
import dino.config
import dino.db.schema  
from session import ElementSession

class DbConfig(object):
    """
    A DbConfig is comprised of two things:
        1. Database connection information 
            Driver, URL, username/password, etc
             
        2. Set of Entities / MetaData to use with that information.
            Entities = SqlAlchemy Mapped Classes 
            Metadata = Table/Schema Information
    
    By default, the DbConfig uses the ElementSession class to create sessions
    
    The ChangeSetSession, by design, has, at most, a single 
    ChangeSet object available at all times, for revisioned objects to use.
    Since it only has one ChangeSet instance, it can only use one 
    ChangeSet entity, and thus can really only accommodate by 
    definition can only create on ChangeSet object for a given session.  
    
    The default is the entity_set at:
         dino.db.schema.entity_set
    """
    
    URI = "mysql://%(credentials)s@%(host)s/%(db)s"

    BASE_OPTS =  {
        'user' : None,
        'password' : None,
        'host' : None,
        'db' : None,
        'url' : None,
    }

    @classmethod
    def create(cls, **kwargs):  
        '''
        Create a DbConfig using values via config files, and passed in keyword args.
        '''          
        opts = dict(cls.BASE_OPTS)
        
        file_section = kwargs.get('file_section', "db")        
        file_config = dino.config.load_config(file_section)
        if file_config is None:
            raise DbConfigError("Cannot find file section: %s" % file_section)
        
        #import pdb;pdb.set_trace()
        if int(file_config.get('sql_debug', '0')):
            DbConfig.setup_sql_handler()

        
        # check files first  
        for k in opts.keys():  
            if file_config.has_key(k):
                opts[k] = file_config[k]
        
        # Options override fileconfig (eg cli options)
        for k in opts.keys():            
            value = kwargs.get(k)
            if value is not None:
                opts[k] = value
                    
        return DbConfig(**opts)


    def __init__(self, **kwargs):
        self.uri = self._create_uri(kwargs)         
        self.engine = engine.create_engine(self.uri, echo=False)
        
        self.entity_set = kwargs.get('entity_set')
        if self.entity_set is None:
            self.entity_set = dino.db.schema.entity_set
        
        self.metadata_set = set([ e._descriptor.metadata for e in self.entity_set])
        
        for md in self.metadata_set:
            md.bind = self.engine
        
        self.use_changesets = self.entity_set.has_entity("ChangeSet") 
        
        self._schema_info_queried = False
        self._schema_info = None
    
    def __str__(self):
        return "DbConfig<%s>" % self.uri 

    def _create_uri(self, kwargs):
        if kwargs.has_key('url') and kwargs['url'] is not None:
            return kwargs['url']
            
        kwargs.setdefault('user', 'dino')
        kwargs.setdefault('password', 'dino')
        kwargs.setdefault('host', 'localhost')
        kwargs.setdefault('db','test')
    
        for arg in ('user', 'password', 'host', 'db'):
            setattr(self, arg, kwargs[arg])
        
        if kwargs['password'] is not None:
            kwargs['credentials'] = "%s:%s" % (kwargs['user'], kwargs['password'])
        else:
            kwargs['credentials'] = kwargs['user']
            
        return DbConfig.URI % kwargs

    def session(self, check_version=True):
        if check_version:
            if self.entity_set.has_entity("SchemaInfo") and self.schema_info is not None:
                self.schema_info.assert_version_match()
    
        return ElementSession(bind=self.engine, autocommit=True, autoflush=False, entity_set=self.entity_set)
        
    
    @property
    def schema_info(self):
        if not self.entity_set.has_entity("SchemaInfo"):
            return None
            
        if not self._schema_info_queried:
            session = self.session(check_version=False)
            self._schema_info = self.entity_set.resolve("SchemaInfo").find(session, self.db)                        
            session.close()                        
            self._schema_info_queried = True
            
            if self._schema_info is None:
                self.log.warning("No schema version is present")
            
        return self._schema_info
                                        
    def assert_unprotected(self):      
        if self.schema_info and self.schema_info.protected:
            raise CommandExecutionError(self, "Cannot run command against protected db instance: %s" % self)
    
    def connection(self):
        return self.engine.connect()
    
    def resolve(self, entity_name):
        return self.entity_set.resolve(entity_name)
    
    @staticmethod
    def object_session(instance):
        return sqlalchemy.orm.session.object_session(instance)
        
        
    #
    # Testing / Maintenance methods
    #        
    def create_all(self, conn=None):
        s = self.session()
        
        for md in self.metadata_set:
            md.create_all(s.connection())
            
        if self.entity_set.has_entity("SchemaInfo"):            
            self.entity_set.resolve("SchemaInfo").create(s)            
            
        s.close()
       
    def drop_all(self):
        self.engine.execute("SET FOREIGN_KEY_CHECKS = 0")
        for md in self.metadata_set:
            md.drop_all(self.engine)
        self.engine.execute("SET FOREIGN_KEY_CHECKS = 1")

    def clear_schema(self):
        #if self.db is None:
        #    raise  

        connection = self.engine.connect()
        connection.execute("SET FOREIGN_KEY_CHECKS = 0")         

        t = connection.begin()
        
        #tables_stmt = "SELECT table_name FROM information_schema.tables WHERE table_schema = '%s';" % self.db_config.db
        tables_stmt = "SHOW TABLES"
        for row in connection.execute(tables_stmt):
            self.log.fine("Drop Table: %s" % row[0])
            connection.execute("DROP TABLE %s" % row[0])

        t.commit()
        
        connection.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    def truncate_all(self):
        connection = self.engine.connect()
        connection.execute("SET FOREIGN_KEY_CHECKS = 0")         

        t = connection.begin()
        
        tables_stmt = "SHOW TABLES"
        for row in connection.execute(tables_stmt):
            self.log.info("Truncate Table: %s" % row[0])
            connection.execute("TRUNCATE TABLE %s" % row[0])

        t.commit()
        connection.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    def dump_schema(self):
        import StringIO
        buf = StringIO.StringIO()        
        engine = sqlalchemy.engine.create_engine('mysql://', strategy='mock', executor=lambda s: buf.write(s + ";\n"))
            
        for md in self.metadata_set:        
            md.create_all(engine)
            
        return buf.getvalue()
       
    @classmethod
    def setup_sql_handler(cls):
        engine_logger = logging.getLogger("sqlalchemy.engine")
        engine_logger.setLevel(logging.INFO)
        engine_logger.propagate = 0   
        cls.sql_logging_handler = SqlLoggingHandler()
        engine_logger.addHandler(cls.sql_logging_handler)

class_logger(DbConfig)




class SqlLoggingHandler(logging.Handler):
    SQL_REGEX_SET = [ 
        re.compile("\s*(SELECT).*FROM\s+(\S*)\s+(WHERE.*)?", re.I),
        re.compile("\s*(UPDATE)\s*(\S*)\s*.*", re.I),
        re.compile("\s*(INSERT)\s+(?:INTO)?\s*(\S*)\s*.*", re.I),
        re.compile("\s*(DELETE)\s*(\S*)\s*.*", re.I)
    ]
    #PARAM_REGEX = re.compile('([^[]?.*)', re.I)
    
    def __init__(self):
        logging.Handler.__init__(self, level=logging.DEBUG)
        self._scope = None
    
#    def _enable(self):
#        self.setLevel(logging.INFO)
#        
#    def _disable(self):
#        self.setLevel(logging.WARN)

    def emit(self, record):
        scope = self.find_app_scope()            
        if self._scope != scope:
            self._scope = scope            
            s = self._scope[-1]
            print "[sql-listener:scope]: %s[%s].%s" % (s[0], s[1], s[2])
            
        text = self.parse_text(record.msg)
        
        if text:
            print "[sql-listener:sql]:      %s" % text
        
    def parse_text(self, text):
        text = text.replace('\n'," ")
        #print "MESSAGE: ", text            
        for i,regex in enumerate(self.SQL_REGEX_SET):
            m = regex.search(text)
            if m:                
                values = [ v for v in  m.groups() if v ]
                return re.sub('\s+', " ", " ".join(values))
                
        return None

    def find_app_scope(self):
        import traceback
        me = __name__.replace('.','/')
        root = __file__[:-len(me)+1]
        stack = traceback.extract_stack()
        
        del stack[-3:]  # Remove us from the stack
        
        for scope in reversed(stack):
            if scope[0].startswith(root):
                idx = stack.index(scope)
                return stack[0:idx+1]



