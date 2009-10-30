import sys
import os
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.NOTSET)

#
# Major Hack to get around multiple installs of package sqlalchemy
# Should be using pkg_resources.py
# This is only necessary on Gentoo...in Fedora we use Virtualenv
eggs = [ "SQLAlchemy-0.5.3-py2.4.egg", "SQLAlchemy-0.5.3-py2.6.egg"]
for p in sys.path[:]:
    for egg in eggs:
        fullname = os.path.join(p, egg)
        if os.path.exists(fullname):
            sys.path.insert(sys.path.index(p), fullname)

#sys.path.insert(0, "/mnt/hgfs/nicholas/Documents/workspace/SQLAlchemy-0.5.3/lib/")

import sqlalchemy
if sqlalchemy.__version__ not in  [ "0.5.3", "0.5.4p2" ]:
    raise RuntimeError("Found wrong version of SqlAlchemy: %s" % sqlalchemy.__version__)


def class_logger(cls, level=None):
    logger = logging.getLogger(cls.__module__ + "." + cls.__name__.lower())
    cls.log = logger


METHOD_TEMPLATE = """\
def _log_method(self, msg, *args, **kwargs):
    level = %s
    if self.manager.disable >= level:
        return
    if level >= self.getEffectiveLevel():
        self._log(level, msg, args, **kwargs)
"""

# 20 INFO
# 18 FINE
# 16 FINER
# 14 FINEST
# 10 DEBUG
def setup_logging_levels():
    # Just for the fun of it, add new logging levels to the infrastructure
    for (level, name) in ((14, 'FINEST'), (16, 'FINER'), (18, 'FINE')):
        logging.addLevelName(level, name)
        setattr(logging, name, level)

        exec METHOD_TEMPLATE % level
        _log_method.func_name = name.lower()

        setattr(logging.Logger, _log_method.func_name, _log_method)


setup_logging_levels()
