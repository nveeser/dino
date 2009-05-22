import os, sys
import tempfile
import logging
from optparse import Option

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand
from dino.cmd.exception import *
from dino.db import *
#from dino.db.objectspec import *
#from dino.db.element_form import ElementFormProcessor
#from dino.db.exception import *

#import pprint; pp = pprint.PrettyPrinter(indent=2).pprint


class ElementCommand(MainCommand):
    NAME = None
    
    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specify one EntityName / ElementName")  

    
    def _find_element(self, session, assert_class=None):
        try:            
            oname = ObjectSpec.parse(self.args[0], expected=ElementName)
              
            if assert_class and oname.entity_name != assert_class:
                raise CommandArgumentError(self, "EntityName must be: %s" % assert_class)
            
            return session.resolve_element_spec(oname)
                          
        except InvalidObjectSpecError, e:
            raise CommandArgumentError(self, "Invalid ObjectSpec: %s" % e)
        except UnknownElementError, e:
            raise CommandExecutionError(self, str(e)) 
        
        
    def _find_elements(self, session):
        try:
            onames = [ ObjectSpec.parse(a, expected=ElementName) for a in self.args ]         
            return [ session.resolve_element_spec(onames) for onames in onames ]

        except InvalidObjectSpecError, e:
            raise CommandArgumentError(self, "Invalid ObjectSpec: %s" % e)
        except UnknownElementError, e:
            raise CommandExecutionError(self, str(e)) 

    def _create_instances(self, session):
        try:
            return [ session.resolve_entity(a).create_empty() for a in self.args ]                     

        except UnknownEntityError, e:
            raise CommandArgumentError(self, str(e)) 


            
class ElementFormCommand(ElementCommand):                   
    NAME = None

    @with_session
    def execute(self, session):
        processor = ElementFormProcessor.create(session)
               
        # Outfile: -o
        # 
        if self.option.out:   
            form = self.create_form(session, processor)
            self.write_form(form)
            
        # Infile: -i
        #      
        elif self.option.input:
            form = self.read_form()
            self.process_form(session, processor, form)
        
        # Editor: (not -i or -o)
        #
        else:       
            form = self.create_form(session, processor)                   
            new_form = self.edit_form(form) 
            
            if new_form == form:
                self.log.info("Form unchanged: Not Submitting")
                return
            try:            
                self.process_form(session, processor, new_form)
            except Exception, e:
                self.log.error("Error Processing form: %s", e)
                self.error_dump_form(new_form)
                raise
            
    
    def write_form(self, form):                    
        if not self.option.file:
            print(form)            
        else:
            f = open(self.option.file, 'w')
            f.write(form)
            f.close()
    
                
    def read_form(self):
        if not self.option.file:
            form = sys.stdin.read()
        else:
            f = file(self.option.file)
            form = f.read()
            f.close()
    
        return form

    def edit_form(self, form):
        (fd,path) = tempfile.mkstemp(prefix="dino.edit.", suffix=".json", dir="/var/tmp")
        
        os.write(fd, form)
        os.close(fd)  
        
        if os.environ.has_key("VISUAL"):
            editor = os.environ["VISUAL"]
        elif os.environ.has_key("EDITOR"):
            editor = os.environ["EDITOR"]
        else:
            editor = "/usr/bin/vi"
        
        os.spawnv(os.P_WAIT, editor, [ editor, path] )
        
        form = open(path).read()        
        os.unlink(path) 
        
        return form
        
    def error_dump_form(self, form):
        for i in range(1, 20):
            filename = "dino.edit.%d" % i
            if not os.path.exists(filename):
                break
                
        f = open(filename, 'w')
        f.write(form)
        f.close()
        self.log.info("Writing current form to file: %s", filename)
        
        
    def create_form(self, session, processor): 
        raise NotImplementedError()

    def process_form(self, processor, form):
        raise NotImplementedError()
                    

            
        
class EditCommand(ElementFormCommand):    
    '''
    Edit the specified Element Instance(s)
    
    ObjectSpecList := <ObjectSpec> [ <ObjectSpec> [ ... ] ]
    
    See 'help objectspec' for more info on EntityName 
    '''
    NAME = "edit"
    USAGE = "{ -i | [ -o ] <ObjectSpecList> } [ -f <filename> ] "
    GROUP = "element" 
    OPTIONS = ( 
        Option('-o', dest='out', action='store_true', default=False), 
        Option('-i', dest='input', action='store_true', default=False), 
        Option('-f', dest='file', default=None),
        Option('-n', '--no-commit',  dest='no_commit', action='store_true', default=False), 
        )

    def validate(self):            
        if len(self.args) < 1 and not self.option.input:
            raise CommandArgumentError(self, "Must specify an ElementName (<EntityName>/<InstanceName>)")  

    def create_form(self, session, processor):                
        instances = self._find_elements(session)
        
        processor.show_headers = len(instances) == 1

        return processor.to_form(instances)



    def process_form(self, session, processor, form):
        desc = processor.update_all(form, force_rollback=self.option.no_commit)
        
        for change in desc:
            self.log.info(str(change))
        
        if self.option.no_commit:
            self.log.info("no-commit specified: nothing submitted")
            
        elif session.last_changeset:
            self.log.info("Submitted: %s", session.last_changeset)
            
        else:
            self.log.info("No Change: Not Submitted")
        
            
            
class CreateCommand(ElementFormCommand):
    '''
    Create a new instance(s) of the specified Element type(s)
    
    EntityNameList := <EntityName> [ <EntityName> [ ... ] ]
    
    See 'help objectspec' for more info on EntityName 
    '''
    NAME = "create"
    USAGE = " { -i | [ -o ] <EntityNameList> } [ -f <filename> ]"
    GROUP = "element"
    OPTIONS = ( 
        Option('-o', dest='out', action='store_true', default=False), 
        Option('-i', dest='input', action='store_true', default=False), 
        Option('-f', dest='file', default=None), 
        Option('-n', '--no-commit',  dest='no_commit', action='store_true', default=False),
        )

    def validate(self):            
        if len(self.args) < 1 and not self.option.input:
            raise CommandArgumentError(self, "Must specify an EntityName")  

        for a in self.args:
            if ObjectSpec.SEPARATOR in a:
                raise CommandArgumentError(self, "Argument looks like a ElementName, not EntityName: %s" % a)

    def create_form(self, session, processor):       
        instances = self._create_instances(session)
        processor.show_headers = len(instances) == 1
        return processor.to_form(instances)
       

    def process_form(self, session, processor, form):               
        desc = processor.create_all(form, force_rollback=self.option.no_commit)      
        
        for change in desc:
            self.log.info(str(change))
        
        if self.option.no_commit:
            self.log.info("no-commit specified: nothing submitted")
            
        else:
            self.log.info("Submitted: %s", session.last_changeset)
    

            
class DumpCommand(EditCommand):
    '''
    Dump the contents of the specified Element(s)
    
    ObjectSpecList := <ObjectSpec> [ <ObjectSpec> [ ... ] ]
    
    See 'help objectspec' for more info on ObjectSpec 
    '''
    NAME = "dump"
    USAGE = "<ElementNameList> [ -f <filename> ]"
    GROUP = "element"
    OPTIONS = ( 
        Option('-f', dest='file', default=None), 
        )       

    def validate(self):            
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specify an ElementName (<EntityName>/<InstanceName>)")  

    @with_session
    def execute(self, session): 
        processor = ElementFormProcessor.create(session, show_read_only=True)
        instances = self._find_elements(session)
        
        processor.show_headers = len(instances) == 1
        
        form = processor.to_form(instances)                                
        self.write_form(form)
            
     