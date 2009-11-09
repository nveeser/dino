import os, sys
import tempfile
import logging
from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.cmd.exception import *
from dino.db import *



class ElementCommand(DinoCommand):
    NAME = None

    def validate(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, "Must specify one EntityName / ElementName")


    def _find_element(self, args, session, assert_class=None):
        try:
            resolver = session.spec_parser.parse(args[0], expected=ElementNameResolver)

            if assert_class and resolver.get_entity() != assert_class:
                raise CommandArgumentError(self, "EntityName must be: %s" % assert_class)

            return resolver.resolve(session).next()

        except InvalidObjectSpecError, e:
            raise CommandArgumentError(self, "Invalid ObjectSpec: %s" % e)
        except UnknownElementError, e:
            raise CommandExecutionError(self, str(e))


    def _find_elements(self, args, session):
        try:
            for a in args:
                resolver = session.spec_parser.parse(a, expected=ElementNameResolver)
                for elmt in resolver.resolve(session):
                    yield elmt

        except InvalidObjectSpecError, e:
            raise CommandArgumentError(self, "Invalid ObjectSpec: %s" % e)
        except UnknownElementError, e:
            raise CommandExecutionError(self, str(e))





class ElementFormCommand(ElementCommand):
    NAME = None

    def create_processor(self, session):
        raise NotImplementedError()

    def process_form(self, opts, session, processor, form):
        raise NotImplementedError()

    @with_session
    def execute(self, opts, args, session):
        processor = self.create_processor(session)

        # Infile: -i
        #      
        if opts.input:
            form = self.read_form(opts)
            self.process_form(opts, session, processor, form)

        # Editor: (not -i or -o)
        #
        else:
            elements = list(self._find_elements(args, session))
            processor.show_headers = len(elements) == 1
            form = processor.to_form(elements)

            if opts.out:
                self.write_form(opts, form)

            else:
                new_form = self.edit_form(opts, form)

                if new_form == form:
                    self.log.info("Form unchanged: Not Submitting")
                    return
                try:
                    self.process_form(opts, session, processor, new_form)
                except Exception, e:
                    self.log.error("Error Processing form: %s", e)
                    self.error_dump_form(new_form)
                    raise


    def write_form(self, opts, form):
        if not opts.file:
            print(form)
        else:
            f = open(opts.file, 'w')
            f.write(form)
            f.close()


    def read_form(self, opts):
        if not opts.file:
            form = sys.stdin.read()
        else:
            f = file(opts.file)
            form = f.read()
            f.close()

        return form

    def edit_form(self, opts, form):
        (fd, path) = tempfile.mkstemp(prefix="dino.edit.", suffix=".json", dir="/var/tmp")

        os.write(fd, form)
        os.close(fd)

#        editor = None
#        for path in (os.environ.get("VISUAL"), os.environ.get("EDITOR"), "/usr/bin/vi", "/bin/vi", "/usr/bin/vim"):
#            if path is not None and os.path.exists(path):
#                editor = path
#
#        if editor is None:
#            raise CommandExecutionError("Could not find editor: set environment variable VISUAL or EDITOR")

        if os.environ.has_key("VISUAL"):
            editor = os.environ["VISUAL"]
        elif os.environ.has_key("EDITOR"):
            editor = os.environ["EDITOR"]
        else:
            editor = "/usr/bin/vi"

        os.spawnv(os.P_WAIT, editor, [ editor, path])

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
        Option('-n', '--no-commit', dest='no_commit', action='store_true', default=False),
        )

    def validate(self, opts, args):
        if len(args) < 1 and not opts.input:
            raise CommandArgumentError(self, "Must specify an ElementName (<EntityName>/<InstanceName>)")


    def create_processor(self, session):
        return MultiElementFormProcessor(session)


    def process_form(self, opts, session, processor, form):

        session.begin()

        processor.process(form)

        desc = session.create_change_description()

        try:
            if opts.no_commit:
                self.log.info("Forced Rollback")
                session.rollback()

            else:
                self.log.info("Committing")
                session.commit()

        except Exception, e:
            self.log.info("Error: %s" % e)
            session.rollback()
            raise

        # Tell the user about what changed
        #
        for change in desc:
            self.log.info(str(change))


        if opts.no_commit:
            self.log.info("no-commit specified: nothing submitted")

        elif len(desc) == 0:
            self.log.info("No Change: Not Submitted")

        elif session.last_changeset:
            self.log.info("Submitted: %s", session.last_changeset)

        else:
            self.log.info("Submitted")



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
        Option('-n', '--no-commit', dest='no_commit', action='store_true', default=False),
        )

    def validate(self, opts, args):
        if len(args) < 1 and not opts.input:
            raise CommandArgumentError(self, "Must specify an EntityName")

        for a in args:
            if not self.db_config.object_spec_parser().is_spec(a, expected=EntityNameResolver):
                raise CommandArgumentError(self, "Argument must be an EntityName")

    def create_processor(self, session):
        return MultiElementFormProcessor(session, allow_create=True)


    def _find_elements(self, args, session):
        try:
            for a in args:
                yield session.resolve_entity(a).create_empty()

        except UnknownEntityError, e:
            raise CommandArgumentError(self, str(e))


    def process_form(self, opts, session, processor, form):

        session.begin()

        is_modified = processor.process(form)

        desc = session.create_change_description()

        if opts.no_commit:
            self.log.info("Forced Rollback")
            session.rollback()

        elif is_modified:
            self.log.fine("Element(s) Modified: Commit")
            session.commit()

        else:
            self.log.fine("Element(s) Unchanged: Rollback")
            session.rollback()

        # Tell the user about what changed
        #
        for change in desc:
            self.log.info(str(change))

        if opts.no_commit:
            self.log.info("no-commit specified: nothing submitted")

        elif len(desc) == 0:
            self.log.info("No Change: Not Submitted")

        elif session.last_changeset:
            self.log.info("Submitted: %s", session.last_changeset)

        else:
            self.log.info("Submitted")



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

    def validate(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, "Must specify an ElementName (<EntityName>/<InstanceName>)")

    @with_session
    def execute(self, opts, args, session):
        processor = MultiElementFormProcessor(session, show_read_only=True)
        elements = list(self._find_elements(args, session))

        processor.show_headers = len(elements) == 1

        form = processor.to_form(elements)

        self.write_form(opts, form)

