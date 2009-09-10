import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props   

from dino.cmd import MainCommand
from dino.cmd.exception import CommandArgumentError
from dino.db import schema, ObjectSpec, Element, ResourceElement



class HelpCommand(MainCommand):
    ''' Specify the help string (doc string) for a given command or schema object'''
    
    NAME = "help"
    USAGE = "[ commands | entities | objectspec | <Command> | <EntityName> ]"
    GROUP = "system"
    
    def execute(self):
        if len(self.args) > 0:
            argument = self.args[0]
            
            if argument == "entities":
                self.list_entities()
                
            elif argument == "commands": 
                self.list_commands()
            
            elif argument == "objectspec":
                print ObjectSpec.__doc__
                
            elif schema.entity_set.has_entity(argument):
                entity = schema.entity_set.resolve(argument)    
                self.print_entity(entity)
                
            elif MainCommand.has_command(argument):            
                cmd_class = MainCommand.find_command(self.args[0])
                cmd = cmd_class(self.db_config, self.cli)
                self.print_command(cmd)
                     
            else:
                raise CommandArgumentError(self, "Cannot provide help for unknown object: " + argument)      
                            
        else:
            self.print_usage()
            print "For a list of commands:"
            print "%s help commands" % self.cli.prog_name
            print
            print "For a list of elements:"
            print "%s help elements" % self.cli.prog_name
            print 
            print "For the ObjectSpec description"
            print "%s help objectspec" % self.cli.prog_name
    
    
    @staticmethod
    def list_entities():
        print "<EntityName> :="
        for entity in schema.entity_set:
            if issubclass(entity, Element):
                if entity.is_revision_entity():
                    continue
                if entity.has_revision_entity():                
                    print "  %s (R)" % entity.__name__
                else:
                    print "  %s" % entity.__name__

    @staticmethod
    def list_commands():
        print "<Command> :="
        for group, cmds in MainCommand.GROUPS.iteritems():
            print "  %s:" % group
            for c in cmds:
                if isinstance(c.NAME, (list,tuple)):
                    print "     " + "|".join(c.NAME) + " " + c.USAGE
                else:
                    print "     " + c.NAME + " " + c.USAGE
            print

    def print_command(self, cmd):            
        cmd.print_usage()
        print "Description:"
        if hasattr(cmd, '__doc__') and cmd.__doc__ is not None:
            print cmd.__doc__
        else:             
            print "  <Command has no doc>  "
            
        cmd.print_help()

    def print_entity(self, entity):
        print entity.entity_display_processor().show(entity)
  
    def _print_doc(self, docstr, indent=""):
        ''' Print out the docstring, removing any whitespace begining or ending the line
            Add specified indentation.
        '''
        for line in docstr.split('\n'):
            line = line.strip()
            print indent + line
    

    
