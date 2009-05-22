import sys
import os
import subprocess
import logging, traceback
from optparse import OptionParser
from os.path import join as pjoin

import sqlalchemy.exc as sa_exc

from dino.exception import DinoException
import dino.basecli
import dino.config 

class GeneratorException(DinoException):
    pass

class NoSuchGeneratorError(GeneratorException):
    pass

class GeneratorQueryError(GeneratorException):
    pass

class GeneratorExecutionError(GeneratorException):
    pass

try:
    check_call = subprocess.check_call
except AttributeError:
    # Raided straight fom /usr/lib/python2.5/subprocess.py
    def check_call(*popenargs, **kwargs):
        """Run command with arguments.  Wait for command to complete.  If
        the exit code was zero then return, otherwise raise
        CalledProcessError.  The CalledProcessError object will have the
        return code in the returncode attribute.

        The arguments are the same as for the Popen constructor.  Example:

        check_call(["ls", "-l"])
        """
        retcode = subprocess.call(*popenargs, **kwargs)
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        if retcode:
            raise RuntimeError(retcode, cmd)
        return retcode


    
class GeneratorMeta(type): 
    def __init__(cls, name, bases, dict_):
        super(GeneratorMeta, cls).__init__(name, bases, dict_) 
 
        cls.log = logging.getLogger("dino.generate." + name)
  
        if bases[0] == object:
            cls.MAP = {}     
            return 
                 
        if not hasattr(cls,'NAME'):
            raise Exception("Subclass must define NAME: %s" % name)
        
        cls.activate = cls.activate_decorator(cls.activate)
         
        if cls.NAME is None:
            return        
        else:
            cls.MAP[cls.NAME] = cls
    
    def activate_decorator(cls, fn):
        def new_activate(self):
            if not int(self.settings.disable_activate):
                return fn(self)
            else:
                self.log.info("Activate is disabled")
                return None
                
        new_activate.__doc__ = fn.__doc__
        new_activate.__name__ = fn.__name__
        return new_activate
        
class Generator(object):    
    __metaclass__ = GeneratorMeta
        
    PROG_NAME = "dino"
    
    #
    # Default/Abstract Instance Methods
    #
    def __init__(self, db_config):
        self.db_config = db_config                    
        self.settings = dino.config.load_config(section="generate")
        self.workdir = pjoin(self.settings.workdir, self.NAME)
   
    @classmethod
    def find_generator_class(cls, name):
        if name in cls.MAP:
            return cls.MAP[name]
        else:
            return None
    @classmethod
    def get_generator_class(cls, name):
        g = cls.find_generator_class(name)
        if g is not None:
            return g
        else:
            raise NoSuchGeneratorError(name)
   
    @classmethod
    def generator_class_iterator(cls, exclude=()):
        if not isinstance(exclude, (list, tuple, set)):
            exclude = (exclude,)
        
        for g in cls.MAP.values():
            if g in exclude or g.NAME in exclude:
                continue
            yield g
   
    def parse(self, args):
        if hasattr(self, 'OPTIONS'):
            parser = OptionParser()
            assert isinstance(self.OPTIONS, (tuple, list)), "%s.OPTIONS must be a tuple or list" % self.__class__.__name__
            for opt in self.OPTIONS:
                parser.add_option(opt)
            (self.option, self.args) = parser.parse_args(args)
        else:
            self.option = None
            self.args = args
            
   
    def generate(self): 
        raise NotImplementedError("_generate")
        
    def activate(self): 
        raise NotImplementedError("_activate")



    # helper methods for (un)setting a lock during generation and activation
    # of the various services
    def lock(self, pname):
        lock_dir = self.settings.lock_dir
        if not os.path.exists(lock_dir):
            os.makedirs(lock_dir)
        lock_file = os.path.join(lock_dir, '%s.lock' % pname)
        # try to lock file - fail if you cannot
        try:
            fd = open(lock_file, 'w')
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except IOError, ex:
            if ex.errno == errno.EACCES or ex.errno == errno.EAGAIN:
                # lock could not be acquired - close fd and error out
                fd.close()
                self.log.error('%s is locked for operation: %s' % (lock_file, pname))
            else:
                self.log.error('could not open lock file %s' % lock_file)
            raise    
    
    def unlock(self, pname, fd):
        lock_dir = self.settings.lock_dir
        if not os.path.exists(lock_dir):
            # somebody messed with var dirs - raise hell
            self.log.error('%s gone before unlock' % lock_dir)
            raise RuntimeError('%s gone before unlock' % lock_dir)
            
        lock_file = os.path.join(lock_dir, '%s.lock' % pname)
        if not os.path.exists(lock_file):
            # why oh why!!
            self.log.error('%s gone before unlock' % lock_file)
            raise RuntimeError('%s gone before unlock' % lock_file)
        # try to lock file - fail if you cannot
        try:
            fcntl.lockf(fd, fcntl.LOCK_UN)
            fd.close()
        except IOError, ex:
            self.log.error('cannot unlock previously locked %s' % lock_file)
            raise   

    @staticmethod
    def setup_dir(dir, wipe=True, default_mode=0755):
        '''clean a directory for use as a dumping ground'''
        from shutil import rmtree
        if wipe and os.path.exists(dir):                
            if os.path.isdir(dir):                    
                rmtree(dir)
            else:
                os.unlink(dir)                
        # make the directory.  permissions?
        os.makedirs(dir, mode=default_mode)

    
    @staticmethod
    def check_call(*args, **kwargs):
        return check_call(*args, **kwargs)

   
    @staticmethod
    def pull_rapids_datacenter(settings, datacenter):
        fp = os.path.join(settings.rapids_root, 'release', 'datacenter', datacenter)
        fd = open(fp, 'r')
        import yaml
        return yaml.load(fd)['tmpl_data']
    
    @staticmethod
    def rsync_directory(src, trg, delete=True, verbose=True, extra_args=()):
        # rsync oddity.  ensure trailing slashes so that it doesn't try to 
        # inject it as a subdir
        src = src.rstrip('/') + '/'
        trg = trg.rstrip('/') + '/'
        args = ['rsync', src, trg, '-ruaHI']
        if verbose:
            args.append('-v')
        if delete:
            args.append('--delete')
        args.extend(extra_args)
        check_call(args)
        
    @classmethod
    def main(cls):
        return GeneratorCli(cls).main(sys.argv[1:])



class GeneratorCli(dino.basecli.CommandLineInterface):    
    
    def __init__(self, generator_cls):
        dino.basecli.CommandLineInterface.__init__(self)
        self.generator_cls = generator_cls
    
    
    def setup_parser(self):
        parser = OptionParser()
        parser.allow_interspersed_args = False    
        parser.add_option('-g', '--generate', action='store_true', default=False, help='generate only')
        parser.add_option('-a', '--activate', action='store_true', default=False, help='activate only')
        parser.add_option('-v', '--verbose', action='callback', callback=self.increase_verbose_cb)
        parser.add_option('-d', '--debug', action='store_true', default=False, help='debug output')
        parser.add_option('-x', '--xception-trace', action='store_true', dest='exception_trace', default=False)
        
        return parser


    def main(self, args):
        try:
            self.setup_base_logger("dino.generate")
        
            parser = self.setup_parser()       
            (options, args) = parser.parse_args(args=args)
            
            db_config = self.create_db_config(options)
            
            gen = self.generator_cls(db_config)
            gen.parse(args)
            
            if options.generate:
                gen.generate(args)
            elif options.activate:
                gen.activate(args)
            else:
                gen.generate(args)
                gen.activate(args)
        
        except GeneratorException, e:
            print "GeneratorException: ", e.args[0]
            if options.exception_trace: e.print_trace()
            sys.exit(-1)
                 
        except sa_exc.DatabaseError, e:
            print "Database Error: %s.%s" % (e.__module__, e.__class__.__name__)
            if e.orig:
                print "\t (%s.%s)" % (e.orig.__module__, e.orig.__class__.__name__)
                args = [ str(a) for a in e.orig.args ]
                print "[ " + ", ".join(args) + " ]"
                
            print "STATEMENT:\n%s" % e.statement
            print "ARGS: %s" % str(e.params)
            
        except KeyboardInterrupt, e:
            print "Ctrl-C"
            sys.exit(1)
        except SystemExit, e:
            pass
        except Exception, e:
            print "Unknown Error: %s.%s" % (e.__module__, e.__class__.__name__)
            print e
            traceback.print_exc()
            sys.exit(1)
        
        
