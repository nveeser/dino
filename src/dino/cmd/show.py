import types
from optparse import Option

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import ( 
    Element, ElementProperty, MultiElementFormProcessor, 
   
    EntityNameResolver, ElementNameResolver, ElementQueryResolver, 
    ElementIdResolver, ElementFormIdResolver, PropertySpecResolver,
        
    ObjectSpecError, UnknownEntityError, UnknownElementError )

#import dino.db.element 

class ShowCommand(MainCommand):
    ''' Show Element(s) and attributes from the repository 
    Multiple ObjectSpecs may be specified, but must be of the same type.
    
    -p --print-sql { ElementQuery, AttributeQuery }
        Print the SQL instead of the results
    -f --form-output  { ElementQuery }
        Print the form output, not the name of the element(s)
    -n --show-name  { AttributeName | AttributeQuery }
        Show Full AttributeName with value  
    '''
    
    NAME = ('show', 'sh')
    USAGE = "<EntityName> | <ElementName> | <ElementId> | <ElementQuery> | <AttributeName>"
    GROUP = "query"
    OPTIONS = ( 
        Option('-p', '--print-sql', dest='print_sql', action='store_true', default=False),
#        Option('-f', '--form-output',  dest='form_output', action='store_true', default=False), 
        Option('-n', '--show-name',  dest='show_name', action='store_true', default=False),  
    )
    
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must at least one argument")



    @with_session
    def execute(self, session):
        
        object_spec_parser = self.db_config.object_spec_parser(
            print_query=self.option.print_sql,
            show_name=self.option.show_name)
        
        try:
            resolvers = [ object_spec_parser.parse(arg) for arg in self.args ]
            
        except ObjectSpecError, e:
            raise CommandArgumentError(self, str(e))
        
        # Use the specific ObjectSpec class to properly 
        # find the results of the each ObjectSpec      
        result = self.resolve_all_specs(session, resolvers)

        if not self.cli:
            return list(result)
               
        for x in result:
            print x

       
    def resolve_all_specs(self, session, resolvers):
        try:  
            for resolver in resolvers:                
                for obj in resolver.resolve(session):
                    if isinstance(obj, type):
                        yield obj.entity_display_processor().show(obj) 
                
                    elif isinstance(obj, Element):
                        yield obj.display_processor().show(obj)        


                    elif isinstance(obj, ElementProperty):                                                        
                        value = obj.valuestr()
                        if self.option.show_name:
                            yield "%s %s" % (obj, value)
                        else: 
                            yield value
                    else:
                        yield obj                    
                        
        except UnknownEntityError, e:
            raise CommandExecutionError(self, str(e))
        except UnknownElementError, e:
            raise CommandExecutionError(self, e)
                         

