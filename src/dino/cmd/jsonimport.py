#!/usr/bin/env python

import os
import logging
from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.cmd.jsonutil import *


class JsonImportCommand(DinoCommand):

    ''' 
    Add a complete device description from a json file.
    If path is a directory, process all files in that 
    directory.  Directories are not processed recursively. 
    '''

    NAME = 'jsonimport'
    USAGE = '<file|dir> [ , <file|dir> ] ... ]'
    GROUP = 'data'
    OPTIONS = (
        Option('-n', '--no-submit', action='store_false', dest='submit', default=True),
    )

    def validate(self, opts, args):
        if len(args) < 1:
            raise CommandArgumentError(self, "Must specify a file/dir to add")


    @with_session
    def execute(self, opts, args, session):
        proc = JsonProcessor(self, session)

        for path in self.arg_iterator(args):
            session.open_changeset()

            # process record
            proc.process(path)

            # submit changes
            if opts.submit:
                cs = session.submit_changeset()
                self.log.info("Committed Changeset: " + str(cs))
            else:
                session.revert_changeset()
                self.log.info("Not submitting")

            session.expunge_all()


    def arg_iterator(self, args):
        for path in args:
            if not os.path.exists(path):
                raise CommandArgumentError(self, "Path does not exist: " + path)

            if os.path.isfile(path):
                yield path

            elif os.path.isdir(path):
                for x in os.listdir(path):
                    filepath = os.path.join(path, x)
                    if os.path.isfile(filepath):
                        yield filepath
            else:
                raise CommandArgumentError(self, "add can only accept dir or file")


