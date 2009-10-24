import os
import logging
import re
from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.cmd.exception import *

from dino.db import Element, schema, DbConfig, __file__ as db_filepath
import pprint; pp = pprint.PrettyPrinter(indent=2).pprint

class MigrateCommand(DinoCommand):
    ''' Create new database instance and migrate data from old instance specified by src_schema '''

    NAME = 'migrate'
    USAGE = ''''''
    GROUP = "system"
    OPTIONS = ()


    def __init__(self, db_config, cmd_env=None):
        DinoCommand.__init__(self, db_config, cmd_env=cmd_env)
        self.upgrades = {}
        self.downgrades = {}


    def execute(self):
        # Create session without checking version
        self.load_files()

        session = self.db_config.session(check_version=False)
        sinfo = schema.SchemaInfo.find(session, self.db_config.db, expunge=False)

        if sinfo is None:
            raise CommandExecutionError(self, "Cannot migrate: Database has no SchemaInfo")

        if sinfo.version == sinfo.model_version:
            self.log.info("Database Version and Model Version are identical")
            return

        while sinfo.version != sinfo.model_version:
            (filepath, new_version) = self.find_migrate_script(sinfo)

            try:
                session.begin()

                self.do_upgrade(session, filepath, new_version)

                sinfo.database_version = new_version

                session.commit()

                if session.last_changeset:
                    self.log.info("Submitted Changeset: %s", session.last_changeset)

            except Exception, e:
                session.rollback()
                raise



        session.begin()

        Element.update_all_names(session)

        desc = session.create_change_description()

        for change in desc:
            self.log.info(str(change))

        session.commit()

    def do_upgrade(self, session, filepath, new_version):
        f = open(filepath)
        sql_script = f.read()
        f.close()

        self.log.info("Running script: %s", filepath)
        conn = session.connection().connection
        cursor = conn.cursor()

        for stmt in sql_script.split(';'):
            if stmt.strip() == "":
                continue

            self.log.finer("Statement: \n%s" % stmt)
            cursor.execute(stmt)


    def find_migrate_script(self, sinfo):

        self.log.info("Schema Version: %s", sinfo.version)
        if sinfo.version == 0x020110:
            return self.upgrades[0]

        elif sinfo.database_version < sinfo.model_version:
            if self.upgrades.has_key(sinfo.database_version):
                return self.upgrades[sinfo.database_version]
            else:
                raise CommandExecutionError(self, "Could not find upgrade script for DB version: %d", sinfo.version)

        else:
            if self.downgrades.has_key(sinfo.database_version):
                return self.downgrades[sinfo.database_version]
            else:
                raise CommandExecutionError(self, "Could not find downgrade script for DB version: %d", sinfo.version)

    def load_files(self):
        regex = re.compile('(\d+)_(\d+).sql')

        migrate_root = os.path.join(os.path.dirname(db_filepath), "migrate")

        for filename in os.listdir(migrate_root):
            m = regex.match(filename)
            if m:
                (start_version, end_version) = map(int, m.groups())
                self.log.info("Found: %s", filename)
                filepath = os.path.join(migrate_root, filename)

                if start_version < end_version:
                    self.upgrades[start_version] = (filepath, end_version)
                else:
                    self.downgrades[start_version] = (filepath, end_version)

