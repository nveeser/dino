import types
from optparse import Option

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *

from dino.db import ( Element, MultiElementFormProcessor, ObjectSpec, 
    EntityName, EntityQuery, ElementName, ElementQuery, AttributeName,
     UnknownEntityError, UnknownElementError )
       
#from dino.db.element_form import ElementFormProcessor
#from dino.db.element import Element
#from dino.db.objectspec import *
#from dino.db.exception import *

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
        Option('-f', '--form-output',  dest='form_output', action='store_true', default=False), 
        Option('-n', '--show-name',  dest='show_name', action='store_true', default=False),  
    )
    
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must at least one argument")

    
    def resolve_all_specs(self, session, specs):
        try:  
            for object_spec in specs:
                for o in object_spec.resolve(session, print_sql=self.option.print_sql):
                    yield o
        
        except UnknownEntityError, e:
            raise CommandExecutionError(self, str(e))
        except UnknownElementError, e:
            raise CommandExecutionError(self, e)
                

    @with_session
    def execute(self, session):
        
        try:
            specs = [ ObjectSpec.parse(arg) for arg in self.args ]
            
        except ObjectSpecError, e:
            raise CommandArgumentError(self, str(e))
            
        spec_types = set(( type(spec) for spec in specs ))
            
        # make sure all the ObjectSpecs are of the same type. 
        if len(spec_types) > 1:
            self.log.error("Cannot mix ObjectSpec types in single command: %s" % spec_types)
            raise CommandArgumentError(self, "More than two types specified: " )
        
        object_spec_type = spec_types.pop() 
        
        # Use the specific ObjectSpec class to properly 
        # find the results of the each ObjectSpec      
        result = list(self.resolve_all_specs(session, specs))

        
        # EntityName
        if object_spec_type is EntityName:
            display_proc = result[0].entity_display_processor()
            result = display_proc.show(result[0])


        # ElementQuery, EntityQuery - Optionally dump as a set of forms
        if object_spec_type in (EntityQuery, ElementQuery) and self.option.form_output:                        
            result = MultiElementFormProcessor(session, show_headers=False).to_form(result)
                
        
        # ElementName - display using Element Specific method
        if object_spec_type is ElementName:
            assert len(result) == 1 and isinstance(result[0], Element), "ElementName type failure"
            display_proc = result[0].display_processor()            
            result = display_proc.show(result[0])

                 
        if object_spec_type in (AttributeName,):
            result = list(self._format_attribute(result))

        if not self.cli:
            return result
        
        if isinstance(result, basestring):
            print result
            
        elif isinstance(result, (list, tuple, types.GeneratorType)):            
            for x in result:
                print str(x)
        else:
            raise RuntimeError("spec types returned invalid result: %s" % type(result))
                

    def _format_attribute(self, result):
        for attr in result:
            value = attr.value()
            
            if isinstance(value, (list, tuple)):
                strings = [ str(x) for x in value]
                value = " ".join(strings)
            
            if self.option.show_name:
                yield "%s %s" % (attr, value)
            else: 
                yield str(value)

            

class DeleteCommand(MainCommand):
    NAME = "delete"
    USAGE = "<ElementNameList>"
    GROUP = "element"
    OPTIONS = (
        Option('-n', '--no-commit',  dest='no_commit', action='store_true', default=False),
    )
   
    def find_elements(self, session):
        try:              
            for a in self.args:
                obj_spec = ObjectSpec.parse(a, expected=(ElementName, ElementQuery))
                
                for inst in obj_spec.resolve(session):
                    yield inst         
                    
        except UnknownEntityError, e:
            raise CommandExecutionError(self, str(e))
        except UnknownElementError, e:
            raise CommandExecutionError(self, e)
   
    @with_session
    def execute(self, session):              

            session.begin() 
        
            for instance in self.find_elements(session):
                session.delete(instance)
            
            desc = session.create_change_description()
            
            for change in desc:
                self.log.info(str(change))

            if self.option.no_commit:
                session.rollback()
                self.log.info("no-commit specified: nothing submitted")
            else:
                session.commit()
                self.log.info("Submitted %s", str(session.last_changeset))


            
        
                

        