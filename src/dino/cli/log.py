import sys, os
import logging

log = logging.getLogger(__name__)

class LogController(object):
    IGNORE_CONFIG_LOGGER_NAMES = [ 'console_format' ]

    def __new__(cls, *args, **kwargs):
        if '_instance' not in vars(cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if 'console_handler' in vars(self):
            return

        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.DEBUG)
        self.console_handler.description = "LogController StreamHandler"

        self.root = logging.getLogger("")
        self.root.setLevel(logging.WARNING)
        self.root.addHandler(self.console_handler)

    def reset(self):
        self.console_handler.setLevel(logging.WARNING)

    def load_config(self):
        file_config = load_config()
        if file_config.has_section("logging"):
            for opt in file_config.options("logging"):
                levelname = file_config.get('logging', opt)
                level = logging.getLevelName(levelname)
                logging.getLogger(opt).setLevel(level)

            format = load_config("logging").console_format
            self._basicformatter = logging.Formatter(format)
            self.console_handler.setFormatter(self._basicformatter)


    def configure(self, options):
        for name, levelname in options.iteritems():
            if name in self.IGNORE_CONFIG_LOGGER_NAMES:
                continue
            level = logging.getLevelName(levelname)
            logging.getLogger(name).setLevel(level)

    def increase_verbose(self):
        level_map = {
            logging.WARNING : logging.INFO,
            logging.INFO : logging.FINE,
            logging.FINE : logging.FINER,
            logging.FINER : logging.FINEST,
            logging.FINEST : logging.DEBUG,
            logging.DEBUG : logging.DEBUG
        }

        curr_level = self.console_handler.level
        for level in level_map.keys():
            if curr_level >= level:
                next_level = level_map[level]

        self.console_handler.setLevel(next_level)

    def setup_base_logger(self, logger_name=""):
        l = logging.getLogger(logger_name)
        l.propagate = False
        l.addHandler(self.console_handler)
        l.setLevel(logging.DEBUG)

LogController()


