"""The base Controller API

Provides the BaseController class for subclassing.
"""

import logging

from pylons.controllers import WSGIController
from pylons import tmpl_context as c
from pylons.templating import render_mako as render
from pylons import session, config, request, response
from dinoweb.model import meta
from pylons.controllers.util import *
from dino.command import AbstractCommandEnvironment

from dino.cli.log import increment_level

class BaseController(WSGIController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            return WSGIController.__call__(self, environ, start_response)
        finally:
            meta.Session.remove()


class DinoCommandController(BaseController):
    def __before__(self):
        self.env = WebCommandEnvironment()

    def __after__(self):
        self.env.remove()
        self.env = None


    def is_traceback(self):
        value = request.params.get('traceback', False)

        try:
            return bool(int(value))
        except ValueError:
            return value

class WebCommandEnvironment(AbstractCommandEnvironment):
    def __init__(self):
        self.output = []
        self._handler = self.InternalHandler(self, level=logging.WARNING)
        f = logging.Formatter("%(levelname)-5.5s [%(name)s] %(message)s")
        self._handler.setFormatter(f)

        self._output_logger = logging.getLogger("OUTPUT")
        self._base_logger = None


        level = request.params.get('loglevel')
        if level is not None:
            self._parseLevelParam(level)

    def write(self, msg=""):
        self._output_logger.info(msg)

    def prog_name(self):
        return "dinoweb"

    def remove(self):
        if self._base_logger is not None:
            self._base_logger.removeHandler(self._handler)

    def setup_base_logger(self, logger_name=""):
        ''' Called by DinoCommand constructor to initialize logging for output '''
        self._base_logger = logging.getLogger(logger_name)
        self._base_logger.addHandler(self._handler)

        self._output_logger = logging.getLogger("%s.OUTPUT" % logger_name)

    def increase_verbose(self):
        next_level = increment_level(self._handler.level)
        self._handler.setLevel(next_level)

    def increase_verbose_cb(self, option, opt, value, parser):
        self.increase_verbose()

    def get_config(self, section=None):
        return {}

    def _parseLevelParam(self, level):
        try:
            level = int(level)
            # Look for a level that has the exact value
            if level in logging._levelNames.keys():
                self._handler.setLevel(level)

            # else call increase verbose N times.
            else:
                for i in xrange(0, level):
                    self.increase_verbose()

        except ValueError:
            # It's not an int, see if it's a string 
            if level in logging._levelNames.keys():
                level = logging.getLevelName(level)
                self._handler.setLevel(level)



    class InternalHandler(logging.Handler):
        def __init__(self, env, **kwargs):
            logging.Handler.__init__(self, **kwargs)
            self.env = env

        def emit(self, record):
            try:
                msg = self.format(record)
                self.env.output.append(msg)

            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)
