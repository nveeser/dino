from optparse import Option

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import ObjectSpec, ElementQuery

class QueryCommand(MainCommand):
    ''' Query repository '''
    
    NAME = 'query'
    USAGE = "<ElementQuery>"
    GROUP = "deprecated"
    OPTIONS = ( 
        Option('-p', dest='print_sql', action='store_true', default=False), 
    )
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must supply a single query")
            
    @with_session
    def execute(self, session):
        
        obj_query = ObjectSpec.parse(self.args[0], expected=ElementQuery)
        
        if self.option.print_sql:
            print obj_query.create_query(session)
            return
         
        for inst in session.query_instances(obj_query):
            print inst
        