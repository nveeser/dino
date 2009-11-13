import types
from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.command import *

from dino.db import (
    Element, ElementProperty, MultiElementFormProcessor,

    EntityNameResolver, ElementNameResolver, ElementQueryResolver,
    ElementIdResolver, ElementFormIdResolver, PropertySpecResolver,

    ObjectSpecError, UnknownEntityError, UnknownElementError)


class DeleteCommand(DinoCommand):
    NAME = "delete"
    USAGE = "<ElementNameList>"
    GROUP = "element"
    OPTIONS = (
        Option('-n', '--no-commit', dest='no_commit', action='store_true', default=False),
    )

    def find_elements(self, args, session):
        try:
            for a in args:
                expected = (ElementNameResolver, ElementQueryResolver, ElementIdResolver)
                resolver = session.spec_parser.parse(a, expected=expected)

                for elmt in resolver.resolve(session):
                    yield elmt

        except UnknownEntityError, e:
            raise CommandExecutionError(self, str(e))
        except UnknownElementError, e:
            raise CommandExecutionError(self, e)

    @with_session
    def execute(self, opts, args, session):

        session.begin()

        for elmt in self.find_elements(args, session):
            session.delete(elmt)

        desc = session.create_change_description()

        for change in desc:
            self.log.info(str(change))

        if opts.no_commit:
            session.rollback()
        else:
            session.commit()


        if opts.no_commit:
            self.log.info("no-commit specified: nothing submitted")

        elif len(desc) == 0:
            self.log.info("No Change: Not Submitted")

        elif session.last_changeset:
            self.log.info("Submitted: %s", session.last_changeset)

        else:
            self.log.info("Submitted")


