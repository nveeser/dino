#!/usr/bin/env python

import os
import site
import sys
import shutil
# ok this is totally hacky
# XXX: this assumes that dino-probe and dino-cli are under libexec
#      and that libexec is two level up
site.addsitedir(
    os.path.abspath('%s/../../dino-cli' % os.path.basename(__file__)))
import transactional

import util

# this info is in the DB do we generate this too
COMMON = '''
default full    { rw *; }
default cisco   { type host; portbase 2000; portinc 1; }
default vmware { type host; portbase 9980; portinc 1;}
default * {
        logfile /var/consoles/&;
        timestamp 1hab;
        include full;
        master localhost;
}
'''

# various sanity processors
def sanity_processor(js):
    pass

def generate(write_loc=None, logger=None):
    if logger is None:
        logger = util.setup_logging('console')
    settings = util.get_settings()
    if write_loc is None:
        write_loc = os.path.join(settings.generated_root, 'conserver.cf')

    logger.info("generate: started")
    try:
        logger.debug("generate: pulling data")
        db = None
        try:
            db = transactional.DBSession(transactional.DB_URI)
        except Exception, ex:
            raise
        results = transactional.get_console_hnodes(db)
        conserves = {}
        for result in results:
            console_props = {}
            console_props['id'] = result['id']
            console_props['fqdn'] = result['handle']
            props = transactional.get_console_props(db, result['id'])
            console_props['host'] = props['host']
            console_props['include'] = props['include']
            console_props['baud'] = props['baud']
            conserves[result['id']] = console_props

        hnodes_with_consoles = {}
        results = transactional.get_hnodes_with_consoles(db)
        for result in results:
            hnodes_with_consoles[result['handle']] = \
                    {'conserver': conserves[result['id']], 
                     'port': result['console_port']}
    except (RuntimeError, SystemExit):
        raise
    except Exception, e:
        logger.error("generate: failed pulling data - %s", e)
        raise

    try:
        util.setup_dir(write_loc)
    except (RuntimeError, SystemExit):
        raise
    except Exception, e:
        logger.error("generate: failed ensuring write directory %r: %s",
            write_loc, e)
        raise
    try:
        fp = open(os.path.join(write_loc, 'conserver.cf'), 'w')
        fp.write(COMMON)
        for k, v in conserves.items():
            print >> fp, 'default %s {' % v['fqdn'].split('.', 1)[0]
            print >> fp, '\tinclude %s' % v['include']
            print >> fp, '\thost %s' % v['host']
            print >> fp, '\tbaud %s' % v['baud']
            print >> fp, '}'

        for k, v in hnodes_with_consoles.items():
            conserver = v['conserver'.split('.', 1)[0]]
            print >> fp, 'default %s { include %s; port %d; }' % (
                    v['handle'], conserver, v['port'])
        fp.close()
    except (RuntimeError, SystemExit):
        raise
    except Exception, e:
        logger.error("generate: failed writing to %s: %s", write_loc, e)
        raise

    logger.info("generate: completed")

def activate(generated_root=None, logger=None):
    if logger is None:
        logger = util.setup_logging('console')
    conf_file = os.path.join(generated_root, 'conserver.cf')
    shutil.copy(conf_file, '/etc/conserver.cf')
    try:
        util.check_call(['/etc/init.d/conserver', 'restart'])
    except (RuntimeError, SystemExit):
        raise

commandline_kls = util.CLIParser.derive_parser(__file__, generate, activate)

if __name__ == '__main__':
    commandline_kls().execute_from_argv()
