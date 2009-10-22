#!/usr/bin/python 
import sys
import os
import re
import logging
import shutil
from subprocess import Popen, PIPE, STDOUT
from optparse import OptionParser, make_option
import traceback
import threading
import pwd

try:
    import hashlib
except ImportError:
    import md5 as hashlib


import pysvn


SPEC_TEMPLATE = '''
Name: %(name)s
Version: %(version)s
Release: %(release)s
Packager: %(packager)s
Prefix: %(prefix)s
License: A License
%(project-header)s
%(project-depend)s

%%description
%(project-description)s

%%prep
%%build
%%install
%(install-script)s

%%clean

%(project-pre-script)s

%(project-post-script)s

%(project-preun-script)s

%(project-postun-script)s

%(project-verify-script)s

%%files
%%defattr(-, root, root)

%(files)s

'''

########################################################################
# Logging
########################################################################

class IndentingLogger(logging.Logger):
    ''' Logger for python logging to include indentation levels '''
    def __init__(self, name, level=logging.NOTSET):
        logging.Logger.__init__(self, name, level)
        self._depth = 0

    def _log(self, level, msg, args, exc_info=None, extra=None):
        indent = "  " * self._depth
        logging.Logger._log(self, level, indent + msg , args, exc_info, extra)

    def inc(self):
        self._depth += 1

    def dec(self):
        if self._depth > 0:
            self._depth -= 1

logging.setLoggerClass(IndentingLogger)

def class_logger(cls):
    logger = logging.getLogger(cls.__module__ + "." + cls.__name__.lower())
    cls.log = logger


########################################################################
# Exceptions
########################################################################

class CauseException(Exception):
    '''Base exception that allows a exception chaining '''
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

        if sys.exc_info()[1] is not None:
            (self.__cause__, self.__cause_traceback__) = sys.exc_info()[1:3]
        else:
            (self.__cause__, self.__cause_traceback__) = (None, None)

    def __iter__(self):
        e = self
        while hasattr(e, '__cause__') and e.__cause__ is not None:
            yield e.__cause__, e.__cause_traceback__
            e = e.__cause__
        return

    def print_trace(self, e=None):
        print
        print "TRACEBACK"
        self._print_exception(self, sys.exc_info()[2])

        for cause, cause_tb in self:
            self._print_exception(cause, cause_tb)

    def _print_exception(self, e, tb):
        print
        if hasattr(e, '__module__'):
            print "%s.%s: %s" % (e.__module__, e.__class__.__name__, str(e))
        else:
            print "%s: %s" % (e.__class__.__name__, str(e))

        traceback.print_tb(tb)


# Command Exceptions
#
class CommandException(CauseException):
    '''Base exception for all commands'''

class InvalidCommandError(CommandException):
    '''Cannot find specified command '''

class CommandDefinitionError(CommandException):
    '''Command Class is not created properly'''

class CommandExecutionError(CommandException):
    '''Error during execute of a specific command'''

class CommandArgumentError(CommandExecutionError): pass

# Object Exceptions
# 
class RpmToolException(CauseException): pass

class ProjectInfoException(RpmToolException): pass

class RpmSpecException(RpmToolException): pass

class DeployException(RpmToolException): pass

class DeployFileException(DeployException): pass

class DeployEntryException(DeployFileException): pass

class DeployEntryParseException(DeployFileException): pass



#####################################
# OptionParser
#####################################
class MyOptionParser(OptionParser):
    ''' OptionParser should throw an exception, not just exit'''

    def exit(self, status=0, msg=None):
        raise CommandArugmentError("Error parsing arguments: %s" % msg)

    def error(self, msg):
        raise CommandArgumentError(msg)

#####################################
# Popen Output Handler Thread
#####################################
class ReadThread(threading.Thread):
    THREADS = []
    @classmethod
    def joinall(cls):
        waiting = True
        while waiting:
            waiting = False
            for t in cls.THREADS:
                if t.isAlive():  t.join(0.1)
                waiting |= t.isAlive()

    def __init__(self, name, f):
        threading.Thread.__init__(self, name=name)
        self.daemon = True
        self.f = f

        self.THREADS.append(self)
        self.start()

    def run(self):
        line = self.f.readline()
        while line != "":
            self.handle(line[:-1])
            line = self.f.readline()

    def handle(self, line):
        print "%s: %s" % (self.name, line)

class LogReadThread(ReadThread):
    def __init__(self, name, f, log):
        self.log = log
        ReadThread.__init__(self, name, f)

    def handle(self, line):
        self.log.info("%s: %s", self.name, line.strip())


#####################################
# RPM Spec Creator
#####################################
class RpmSpec:
    '''Create a specfile'''
    def __init__(self, name=None, version=1, release=1, project_root=None):
        self.name = name
        self.version = version
        self.release = release
        self.project_root = project_root
        self.packager = self._getUsername()
        self.buildroot = None
        self._files = []

    def _getUsername(self):
        from pwd import getpwuid
        from os import getuid
        from socket import gethostname
        pwent = getpwuid(getuid())
        hostname = gethostname()
        return "%s<%s@%s>" % (pwent[4], pwent[0], hostname)

    def set_build_root(self, buildroot):
        self._files = []
        self.buildroot = buildroot
        for (dir, dirnames, filenames) in os.walk(buildroot):
            install_dir = dir.replace(buildroot, "")
            for file in filenames:
                self._files.append(os.path.join(install_dir, file))

            if len(filenames) == 0:
                self._files.append("%dir " + install_dir)

        self._files.sort()
        #self.filterFiles()

    def read_file(self, filename, header="", fail=False):
        filepath = os.path.join(self.project_root, filename)
        if not (os.path.exists(filepath) and os.path.isfile(filepath)):
            if fail:
                raise RpmSpecException, "Missing file building RPM specfile: %s" % filename
            else:
                return ""

        f = open(filepath)
        data = f.read()
        f.close()
        return header + data

    def write(self, filename):
        "Open and write to a file the rpmspec"
        try:
            text = SPEC_TEMPLATE % self.value_dict()
            f = open(filename, "w")
            f.write(text)
            f.close()

        except IOError, msg:
            raise RpmSpecException("Could not write to specfile (% s): % s" % (filename, msg))


    def value_dict(self):
        return {
            'name' : self.name,
            'version' : self.version,
            'release' : self.release,
            'packager' : self.packager,
            'buildroot' : os.path.abspath(self.buildroot),
            'prefix'    : "/",
            'project-header' : self.read_file("RPM/header", fail=True),
            'project-depend' : self.read_file("RPM/depend"),
            'project-description' : self.read_file("RPM/description"),
            'install-script' : "",
            'project-pre-script' : self.read_file("RPM/pre.sh", header="%pre\n"),
            'project-preun-script' : self.read_file("RPM/preun.sh", header="%preun\n"),
            'project-post-script' : self.read_file("RPM/post.sh", header="%post\n"),
            'project-postun-script' : self.read_file("RPM/postun.sh", header="%postun\n"),
            'project-verify-script' : self.read_file("RPM/verify.sh", header="%verifyscript\n"),
            'files' : "\n".join(self._files),
        }



########################################################################
# DeployFile
########################################################################
class DeployFile(list):
    class Counter:
        def __init__(self, init=0):
            self._counter = init

        def inc(self):
            self._counter += 1

        def __str__(self):
            return str(self._counter)

    def __init__(self, filename=None, defroot=None):
        self.execed = DeployFile.Counter()
        self.skipped = DeployFile.Counter()
        self.files = DeployFile.Counter()
        self.errors = DeployFile.Counter()

        self.set_default_root(defroot)
        if filename:
            self.load(filename)


    def load(self, deploy_filename):
        try:
            f = open(deploy_filename)
            for rawline in f.readlines():
                self.parse_line(rawline)
            f.close()

        except IOError, e:
            raise DeployFileException, e


    def parse_line(self, rawline):
        entry = DeployEntry.create(rawline, self)
        if entry:
            self.append(entry)

        return self

    def deploy(self, source_root, target_root):
        for entry in self:
            try:
                try:
                    self.log.inc()
                    entry.execute(source_root, target_root)
                    self.execed.inc()
                finally:
                    self.log.dec()

            except EnvironmentError, ex:
                raise DeployEntryException(str(ex))

            except DeployEntryException, ex:
                # This exception should not stop processing
                self.log.info("DeployEntryException: % s" % ex)
                self.errors.inc()
        return self

    def set_default_root(self, path):
        ''' Default Root is the path added to every outgoing file 
         which is specified with a relative path '''

        if path is not None and path[0] == '/':
            self.defroot = path[1:]
        elif path is None:
            self.defroot = ''
        else:
            self.defroot = path


class_logger(DeployFile)

class DeployEntry(object):
    REGEX = re.compile("m|^\s*([^\#\s]+)\s+(\S+)\s*(\S+){0,1}$|")

    @staticmethod
    def create(rawline, deploy_file):
        rawline = rawline.strip()
        rawline = re.sub("#.*$", "", rawline) # remove comments        
        if re.match("^\s*$", rawline):
            return None

        match = DeployEntry.REGEX.match(rawline)
        if match is None:
            raise DeployEntryParseException("this is not a valid line")

        (lhs, rhs, stat) = match.groups()

        for entry_type in (CopyEntry, TouchEntry, SymlinkEntry):
            if entry_type.REGEX.match(lhs):
                return entry_type(lhs, rhs, PermSpec(stat), rawline, deploy_file)

        raise DeployEntryParseException("Invalid Line")

    def __init__(self, lhs, rhs, perm, raw, deploy_file):
        self._lhs = lhs
        self._rhs = rhs
        self._perm = perm
        self._deploy_file = deploy_file
        self._rawline = raw

        # Add default root if the path is relative 
        if self._rhs[0] != '/':
            self._rhs = os.path.join(deploy_file.defroot, self._rhs)
        else:
            self._rhs = self._rhs[1:]

    def execute(self, source, deploy):
        print str(self)

    @staticmethod
    def checkmkdir(target):
        destdir = os.path.dirname(target)
        if not os.path.exists(destdir):
            os.makedirs(destdir)

    def __str__(self):
        return "[%s] [%s]" % (self._lhs, self._rhs)


class_logger(DeployEntry)


class PermSpec(object):

    def __init__(self, perm_spec):
        self.owner = None
        self.group = None
        self.mode = None

        if perm_spec is not None:
            self._parse(perm_spec)

    def _parse(self, perm_spec):
        parts = perm_spec.split(":")

        if len(parts) == 3:
            (self.owner, self.group, self.mode) = parts

        if len(parts) == 2:
            self.owner = parts[0]
            try:
                self.mode = int(parts[1], 8)
            except:
                self.group = parts[1]

        if len(parts) == 1:
            try:
                self.mode = int(parts[0], 8)
            except:
                self.owner = parts[0]

    def set_perm(self, filename):
        if self.owner:
            uid = pwd.getpwnam(self.owner)[2]
            self.log.debug("[P] chown: %d %s", uid, filename)
            os.chown(filename, uid, -1)

        if self.group:
            gid = grp.getgrnam(self.group)[2]
            self.log.debug("[P] chgrp: %d %s", gid, filename)
            os.chown(filename, -1, gid)

        if self.mode:
            self.log.debug("[P] chmod: %o %s", self.mode, filename)
            os.chmod(filename, self.mode)


class_logger(PermSpec)

class CopyEntry(DeployEntry):
    ''' Copy file(s) from (dir | file) to <file> or <dir>'''

    REGEX = re.compile("^[^-].*$")

    def execute(self, source_root, target_root):
        source = os.path.join(source_root, self._lhs)
        target = os.path.join(target_root, self._rhs)

        if not os.path.exists(source):
            raise DeployEntryException("File does not exist %s" % source)

        if os.path.isdir(source):
            self.sync_directory(source, target)

        elif os.path.isfile(source):
            self.sync_file(source, target)


    def sync_file(self, source, target):
        (sourcedir, sourcefile) = os.path.split(source)
        (targetdir, targetfile) = os.path.split(target)

        if not targetfile:
            target = os.path.join(targetdir, sourcefile)

        elif targetfile != sourcefile:
            self.log.warn("Warning: Renaming file: %s -> %s" % (sourcefile, targetfile))

        self.checkmkdir(target)

        if os.path.isfile(target) and self.files_equal(source, target):
            self.log.info("[C] Skip %s --> \t%s" % (self._lhs, self._rhs))
            self._deploy_file.skipped.inc()

        else:
            self.log.info("[C] Copying %s --> \t%s" % (self._lhs, self._rhs))
            shutil.copy2(source, target)
            self._perm.set_perm(target)
            self._deploy_file.files.inc()

    def sync_directory(self, source, target, delete=False, exclude=()):
        # Used to calculate relative paths for each file
        source_len = len(source)
        if source[-1] != '/':
            source_len += 1

        target_len = len(target)
        if target[-1] != '/':
            target_len += 1

        self.log.info("[D] Sync Dir %s --> \t%s" % (self._lhs, self._rhs))

        # clean out stuff that is not supposed to be there if necessary
        if delete:
            for (dir, dirnames, filenames) in os.walk(target):
                relative_path = dir[target_len:]

                for f in filenames:
                    if os.path.join(relative_path, f) in exclude:
                        self._deploy_file.files.inc()
                        continue

                    source_fp = os.path.join(source, relative_path, f)
                    target_fp = os.path.join(target, relative_path, f)

                    if os.path.islink(source_fp) and not os.path.islink(target_fp):
                        self.log.debug("[D] Removing %s", target_fp)
                        self._deploy_file.files.inc()
                        os.unlink(target_fp)

                    if os.path.islink(target_fp) and not os.path.islink(source_fp):
                        self.log.debug("[D] Removing: %s", target_fp)
                        self._deploy_file.files.inc()
                        os.unlink(target_fp)

                    if not os.path.exists(source_fp):
                        self.log.debug("[D] Removing: %s", target_fp)
                        self._deploy_file.files.inc()
                        os.unlink(target_fp)


        for (dir, dirnames, filenames) in os.walk(source):
            relative_path = dir[source_len:]

            # make sure target dir exists
            target_dir = os.path.join(target, relative_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                self._perm.set_perm(target_dir)


            # check all files
            for f in filenames:
                if os.path.join(relative_path, f) in exclude:
                    self.log.debug("[D] Skip %s", source)
                    self._deploy_file.skipped.inc()
                    continue

                source_file = os.path.join(source, relative_path, f)
                target_file = os.path.join(target, relative_path, f)

                if os.path.islink(source_file):
                    link_path = os.readlink(source_file)
                    if os.path.islink(target_file) and link_path == os.readlink(target_file):
                        self.log.debug("[D] Skip (link) %s", source_file)
                        self._deploy_file.skipped.inc()
                        continue

                    self.log.debug("[D] Symlink %s", target_file)
                    os.symlink(link_path, target_file)
                    self._deploy_file.files.inc()

                elif os.path.isfile(source_file):
                    if os.path.exists(target_file) and self.files_equal(source_file, target_file):
                        self.log.debug("[D] Skip %s", target_file)
                        self._deploy_file.skipped.inc()
                        continue

                    self.log.debug("[D] Copy %s", target)
                    shutil.copy2(source_file, target_file)
                    self._perm.set_perm(target_file)
                    self._deploy_file.files.inc()

                else:
                    self.log.debug("[D] Skip %s", source)


    @staticmethod
    def files_equal(filepath1, filepath2):
        def fhash(path):
            f = open(path)
            hash = hashlib.md5(f.read()).digest()
            f.close()
            return hash

        if os.path.getmtime(filepath1) != os.path.getmtime(filepath2):
            return False

        return fhash(filepath1) == fhash(filepath2)



class TouchEntry(DeployEntry):
    REGEX = re.compile("^-$")

    def execute(self, source_root, target_root):
        target = os.path.join(target_root, self._rhs)

        if target.endswith('/'):
            if not os.path.exists(target):
                self.log.info("[T] Touch dir %s" % self._rhs)
                os.makedirs(target)
                self._perm.set_perm(target)
                self._deploy_file.files.inc()

            else:
                self.log.info("[T] Skipping dir %s" % self._rhs)
                self._deploy_file.skipped.inc()

        else:
            if not os.path.exists(target):
                self.log.info("[T] Touch file %s" % self._rhs)

                self.checkmkdir(target)
                open(target, 'w').close()
                self._perm.set_perm(target)
                self._deploy_file.files.inc()

            else:
                self.log.info("[T] Skipping file %s" % self._rhs)
                self._deploy_file.skipped.inc()


class SymlinkEntry(DeployEntry):
    REGEX = re.compile("^-.+")

    def __init__(self, lhs, rhs, perm, raw, deploy_file):
        DeployEntry.__init__(self, lhs, rhs, perm, raw, deploy_file)

        self._lhs = self._lhs[1:]

        if self._lhs[0] != '/':
            self._lhs = os.path.join(deploy_file.defroot, self._lhs)
        else:
            self._lhs = self._lhs[1:]


    def execute(self, source_root, target_root):
        realpath = self._build_realpath()
        symfile = os.path.join(target_root, self._rhs)

        if os.path.islink(symfile):
            if os.readlink(symfile) == realpath:
                self.log.info("[L] Skipping %s -> %s" % (self._lhs, self._rhs))
                self._deploy_file.skipped.inc()
                return

            else:
                self.log.info("[L] Removing old link (%s)" % symfile)
                os.unlink(symfile)

        self.log.info("[L] Linking %s -> %s" % (self._lhs, self._rhs))
        self.log.debug("Link %s -> %s" % (realpath, symfile))

        self.checkmkdir(symfile)
        os.symlink(realpath, symfile)
        self._deploy_file.files.inc()


    def _build_realpath(self):
        """Build the path to the symlink and the file relative to it
        
         -/usr/lib/other/path/to/file /usr/lib/path/to/symlink
        
         /usr/lib/path/to/symlink -> /usr/lib/other/path/to/file 

        realpath => ../../other/path/to/file
                
        becomes equivalent to:
        
        ln -s ../../other/path/to/file /usr/lib/path/to/symlink
        """
        fileparts = self._lhs.split("/")
        linkparts = self._rhs.split("/")

        while fileparts[0] == linkparts[0]:
            fileparts.pop(0)
            linkparts.pop(0)

        for dir in linkparts[:-1]:
            fileparts.insert(0, "..")

        return os.path.join(*fileparts)



########################################################################
# Project Info
########################################################################
class ProjectInfo(object):
    def __init__(self, project_root=None):
        self.name = None
        self.version = None

    def __str__(self):
        return "%s-%s" % (self.name, self.version)

    @classmethod
    def create(cls, root):
        if os.path.isdir(os.path.join(root, ".svn")):
            return SvnProjectInfo(root)
        else:
            raise ProjectInfoException("Could not determine project info for path: %s" % root)


class SvnProjectInfo(ProjectInfo):
    def __init__(self, root):
        self.client = pysvn.Client()
        self.root = os.path.abspath(root)
        info = self.client.info(self.root)
        if info is None:
            raise ProjectInfoException("Cannot get SVN Info")

        self._process_info(info)

    def _process_info(self, info):
        parts = info.url.split('/')
        if parts[-1] == 'trunk':
            self.name = parts[-2]
            self.version = "T%s" % str(info.revision.number)
        else:
            self.name = parts[-3]
            self.version = "R%s.%s" % (parts[-1], str(info.revision.number))



########################################################################
# Command Setup
########################################################################

class CommandMeta(type):
    def __init__(cls, name, bases, dict_):
        super(CommandMeta, cls).__init__(name, bases, dict_)

        cls.log = logging.getLogger("rpmtool." + name)

        # If this class's base class is not a CommandMeta class
        # (ie the base's metaclass is something other than CommandMeta), 
        # then this class is the 'Root'. Add the Dictionary
        base_class_type = type(bases[0])
        if not issubclass(base_class_type, CommandMeta):
            cls.COMMANDS = {}
            return

        if not hasattr(cls, 'NAME'):
            raise CommandDefinitionError("CommandMeta Instance has no NAME attribute: %s" % name)

        if cls.NAME is None:
            return

        cls.COMMANDS[cls.NAME] = cls

        # Create Parser
        cls.parser = MyOptionParser(add_help_option=False)
        if hasattr(cls, 'OPTIONS'):
            opts = getattr(cls, 'OPTIONS')
            assert isinstance(opts, (tuple, list)), "%s.OPTIONS must be a tuple or list" % name
            for opt in opts:
                cls.parser.add_option(opt)

        # wrap all exceptions to be CommandExecutionError
        cls.execute = cls._execute_decorator(cls.execute)

    @staticmethod
    def _execute_decorator(func):
        ''' Wrap all execute methods with this decorator, which is 
        used to handle exceptions more uniformily '''

        def execute_decorator_func(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)

            except RpmToolException, e:
                self.log.debug("Converting ElementException to CommandExecuteError")
                raise CommandExecutionError("ExecutionError: %s" % e)

        return execute_decorator_func
    #
    # Find/Get All Commands
    #
    def has_command(cls, key):
        return cls.COMMANDS.has_key(key)

    def commands(cls):
        return cls.COMMANDS.values()

    def get_command(cls, key):
        ''' Find a command, raise exception if not found'''
        cmd = cls.COMMANDS.get(key)
        if cmd is None:
            raise InvalidCommandError(key)
        return cmd


class Command(object):
    '''Abstract Command Interface 
    Used by Classes which use the CommandMeta metaclass. 
    '''
    __metaclass__ = CommandMeta

    def __init__(self, cli=None):
        self.cli = cli

        if cli is not None:
            # Copy global options from cli
            for opt in self.cli.parser.option_list:
                if not self.parser.has_option(opt.get_opt_string()):
                    self.parser.add_option(opt)

    @property
    def prog_name(self):
        if self.cli:
            return self.cli.prog_name
        else:
            return self.PROG_NAME


    def parse(self, args):
        (options, args) = self.parser.parse_args(args)
        self.cli.handle_global_options(options)
        self.handle_options(options, args)

    @classmethod
    def usage(cls, cli):
        return "%s <global-options> %s %s" % (cli.prog_name, cls.NAME, cls.USAGE)

    @classmethod
    def print_help(cls, cli):
        print cls.usage(cli)
        formatter = cls.parser.formatter
        formatter.store_option_strings(cls.parser)
        for opt in cls.parser.option_list:
            print "      " + formatter.format_option(opt).strip()

        print

    def handle_options(self, options, args):
        pass

    def execute(self):
        raise NotImplemented()

########################################################################
# Command(s)
########################################################################

class DeployCommand(Command):
    '''Deploy files from source dir -> target dir via deploy map'''
    NAME = 'deploy'
    USAGE = "[ -m <mapfile> ] [ <sourcedir> ] <targetdir>"

    OPTIONS = (
        make_option('-m', dest='mapfile', default=None,
            help="Deploy map file to use (Default: RPM/DEPLOYMAP)"),
    )

    def handle_options(self, options, args):
        if options.mapfile is not None:
            self.mapfile = options.mapfile
        elif os.environ.has_key('DEPLOYMAP'):
            self.mapfile = os.environ['DEPLOYMAP']
        else:
            self.mapfile = "DEPLOYMAP"

        if len(args) == 2:
            (source_root, target_root) = args
        elif len(args) == 1:
            source_root = os.getcwd()
            target_root = args[0]
        else:
            raise CommandArgumentError("Must provide a source and target root")

        self.source_root = os.path.abspath(source_root)
        self.target_root = os.path.abspath(target_root)


    def execute(self):
        self.log.info("----- Deploy %s --", self.cli.project_name)

        self.log.debug("Path: %s --> %s", self.source_root, self.target_root)
        self.log.debug("DEPLOYFILE: %s", self.mapfile)

        df = DeployFile(self.mapfile)
        df.deploy(self.source_root, self.target_root)

        self.log.info("----- Deploy %s done: Copied: %s Skipped: %s Errors: %s --", \
           self.cli.project_name, df.files, df.skipped, df.errors)



class RpmSpecCommand(Command):
    '''Generate a specfile for project from input directory'''
    NAME = 'spec'
    USAGE = '[ -S <specfile> ] <buildroot>'

    OPTIONS = (
        make_option('-S', dest='specfile', default=None,
            help="Spec file to create (default: <PROJECT_ROOT>/<PROJECT_NAME>.spec)"),
    )

    def handle_options(self, options, args):
        if options.specfile:
            self.specfile = options.specfile
        else:
            self.specfile = os.path.join(self.cli.project_root, self.cli.project_name + ".spec")

        if len(args) < 1:
            raise CommandArgumentError("Must specify build root")

        self.buildroot = args[0]

    def execute(self):
        rpmspec = RpmSpec(
            name=self.cli.project_name,
            version=self.cli.version,
            project_root=self.cli.project_root)
        rpmspec.set_build_root(self.buildroot)
        rpmspec.write(self.specfile)
        self.log.info("Wrote specfile: %s", self.specfile)


class RpmBuildCommand(Command):
    '''Build Rpm '''
    NAME = 'build'
    USAGE = '[ -S <specfile> ] [ -b <buildroot> ] [ -s <install_script> ] [ -m <deploy_map> ]'
    OPTIONS = (
        make_option('-S', dest='specfile', default="project.spec",
            help="Spec file to create (default: <PROJECT_ROOT>/project.spec)"),
        make_option('-s', dest='install_script', default="RPM/install",
            help="script to run at build time (default: <PROJECT_ROOT>/RPM/install)"),
        make_option('-m', dest='deploymap', default="RPM/DEPLOYMAP",
            help="script to run at build time (default: <PROJECT_ROOT>/RPM/DEPLOYMAP)"),
        make_option('-b', dest='buildroot', default="_buildroot",
            help="script to run at build time (default: <PROJECT_ROOT>/_buildroot)"),
    )

    RPM_COMMAND = [ "rpmbuild",
        "--buildroot", "%(buildroot)s",
        "--define", "_rpmdir %(outdir)s",
        "--define", "_builddir %(projectroot)s",
        "--define", "_build_name_fmt %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm",
        "-bb", "%(specfile)s" ]


    def handle_options(self, options, args):
        self.install_script = options.install_script
        if not os.path.isabs(self.install_script):
            self.install_script = os.path.join(self.cli.project_root, self.install_script)

        self.deploymap = options.deploymap
        if not os.path.isabs(self.deploymap):
            self.deploymap = os.path.join(self.cli.project_root, self.deploymap)

        self.buildroot = options.buildroot
        if not os.path.isabs(self.buildroot):
            self.buildroot = os.path.join(self.cli.project_root, self.buildroot)

        self.specfile = options.specfile
        if not os.path.isabs(self.specfile):
            self.specfile = os.path.join(self.cli.project_root, self.specfile)


    def execute(self):
        if os.path.exists(self.install_script):
            self.install()

        if os.path.exists(self.deploymap):
            self.deploy()

        self.spec()
        self.build()

    def install(self):
        try:
            self.log.info("------ Install %s -----", self.cli.project_name)

            env = {
                'RPMTOOL_BUILD_ROOT' : self.buildroot,
                'RPMTOOL_VERSION' : self.cli.version,
            }
            p = Popen([self.install_script], stdout=PIPE, stderr=PIPE, env=env)
            LogReadThread("OUT", p.stdout, self.log)
            LogReadThread("ERR", p.stderr, self.log)
            p.wait()
            LogReadThread.joinall()

            self.log.info("------ Install (%s) Complete -----", self.cli.project_name)

        except OSError, e:
            raise CommandExecutionError("Error executing install script: %s" % e)

    def deploy(self):
        self.log.info("----- Deploy %s ------", self.cli.project_name)

        self.log.debug("Path: %s --> %s", self.cli.project_root, self.buildroot)
        self.log.debug("DEPLOYFILE: %s", self.deploymap)

        df = DeployFile(self.deploymap)
        df.deploy(self.cli.project_root, self.buildroot)

        self.log.info("----- Deploy %s done: Copied: %s Skipped: %s Errors: %s --", \
            self.cli.project_name, df.files, df.skipped, df.errors)


    def spec(self):
        self.log.info("------ SpecFile -----")

        rpmspec = RpmSpec(
            name=self.cli.project_name,
            version=self.cli.version,
            project_root=self.cli.project_root)

        rpmspec.set_build_root(self.buildroot)
        rpmspec.write(self.specfile)
        self.log.info("Wrote specfile: %s", self.specfile)


    def build(self):
        self.log.info("------ BuildRpm -------")
        vars = {
            'buildroot' : self.buildroot,
            'outdir' : self.cli.project_root,
            'specfile' : self.specfile,
            'projectroot' : self.cli.project_root,
        }
        cmd_args = [ arg % vars for arg in self.RPM_COMMAND ]

        p = Popen(cmd_args, stdout=PIPE, stderr=PIPE)
        LogReadThread("OUT", p.stdout, self.log)
        LogReadThread("ERR", p.stderr, self.log)
        p.wait()
        LogReadThread.joinall()




class HelpCommand(Command):
    ''' Print help / usage '''

    NAME = 'help'
    USAGE = ""

    def handle_options(self, options, args):
        if len(args) > 0:
            self.command_name = args[0]
        else:
            self.command_name = None

    def execute(self):
        if self.command_name:
            cmd_class = Command.get_command(self.command_name)
            cmd_class.print_help(self.cli)
        else:
            self.cli.print_help()


################################################################################
# Command Line Interface
################################################################################
class RpmTool(object):
    ''' Base command line interface for rpmtools 
    Handles 
    - Setup of Logging
    - Handling of Exceptions
    - Initial Argument Parsing
    - Finding / Creating / Executing the Command object
    '''

    OPTIONS = (
        make_option('-v', dest='verbose', action='count', default=0,
            help="Increase verbose"),
        make_option('-R', dest='project_root', default=None,
            help='Root of the project (default is CWD)'),
        make_option('-n', dest='project_name', default=None,
            help='Name of the project (default is determined from SCM)'),
        make_option('-x', dest='traceback', action='store_true', default=False,
            help='Print full traceback of exception'),

    )

    def handle_global_options(self, options):

        if hasattr(options, 'verbose'):
            for i in range(0, options.verbose):
                self.increase_verbose()

        # Project Root
        # 
        if hasattr(options, 'project_root') and options.project_root:
            self.project_root = options.project_root
        elif os.environ.has_key('PROJECT_ROOT'):
            self.project_root = os.environ['PROJECT_ROOT']
        else:
            self.project_root = os.path.abspath(os.getcwd())

        # Project Info (via SCM like Subversion)
        #
        project_info = ProjectInfo.create(self.project_root)

        # Project Version
        #
        self.version = project_info.version

        # Project Name
        #
        if hasattr(options, 'project_name') and options.project_name:
            self.project_name = options.project_name
        elif os.environ.has_key('PROJECT_NAME'):
            self.project_name = os.environ['PROJECT_NAME']
        else:
            self.project_name = project_info.name

        # Exception traceback 
        #
        if hasattr(options, 'traceback'):
            self.traceback = options.traceback


    def __init__(self):
        self.parser = MyOptionParser(usage="", add_help_option=False)
        self.parser.allow_interspersed_args = False
        for opt in self.OPTIONS:
            self.parser.add_option(opt)
        self.setup_logging()

        self.traceback = False
        self.project_root = None
        self.project_name = None
        self.version = None

    def setup_logging(self):
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.INFO)

        root = logging.getLogger("")
        root.setLevel(logging.DEBUG)
        root.addHandler(self.console_handler)

    def increase_verbose(self):
        level_map = {
            logging.WARNING : logging.INFO,
            logging.INFO : logging.DEBUG,
            logging.DEBUG : logging.DEBUG
        }

        curr_level = self.console_handler.level
        for level in level_map.keys():
            if curr_level >= level:
                next_level = level_map[level]

        self.console_handler.setLevel(next_level)


    def usage(self):
        return "%s <global-args> <Command> [ <command-args> ]" % self.prog_name

    def print_usage(self):
        print "For more info: %s help " % self.prog_name
        print "Usage:"
        print self.usage()

    def print_help(self):
        print self.usage()
        print
        formatter = self.parser.formatter
        formatter.store_option_strings(self.parser)
        print "Global Options:"
        for opt in self.parser.option_list:
            print "  " + formatter.format_option(opt).strip()

        print
        print "Commands:"
        for cmd in Command.commands():
            print "%010s : %s" % (cmd.NAME, cmd.__doc__.strip())
        print



    def main(self, argv):
        cmd = None
        try:
            self.prog_name = os.path.basename(argv[0])
            (options, args) = self.parser.parse_args(args=argv[1:])
            self.handle_global_options(options)

            if len(args) < 1:
                raise CommandArgumentError("Must provide a command")

            cmd_name = args.pop(0)
            cmd_class = Command.get_command(cmd_name)
            cmd = cmd_class(self)

            cmd.parse(args)
            cmd.execute()

        except CommandExecutionError, e:
            print e
            if cmd:
                print cmd.usage(self)
            else:
                print self.usage()

            if self.traceback: e.print_trace()
            sys.exit(1)

        except KeyboardInterrupt:
            print "Interrupted"

        except StandardError, msg:
            traceback.print_exc()
            sys.exit(1)

        except Exception, e:
            print "Caught Unknown exception. Message:", e
            self.usage()
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    RpmTool().main(sys.argv)
