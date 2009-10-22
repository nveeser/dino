"""Pylons environment configuration"""
import os
import sys

from mako.lookup import TemplateLookup
from pylons import config
from pylons.error import handle_mako_error
from paste.deploy.converters import asbool

import dinoweb.lib.app_globals
import dinoweb.lib.helpers
from dinoweb.config.routing import make_map
from dinoweb.model import init_model

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='dinoweb', paths=paths)

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = dinoweb.lib.app_globals.Globals()
    config['pylons.h'] = dinoweb.lib.helpers

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # if dino_local is true, assume we are running out of source tree.
    # Add PROJECT_ROOT/src to sys.path
    if asbool(config['dino_local']):
        config['project.root'] = os.path.abspath(os.path.join(root, "..", ".."))
        sys.path.insert(0, os.path.join(config['project.root'], 'src'))

    from dino.db.dbconfig import DbConfig
    db_config = DbConfig.create_from_dict(config, prefix="dino.")
    init_model(db_config)


