#! /usr/bin/env python

'''
Module for all errors that are raised by the Probe module
'''

# TODO: custom error handlers for notifying/alerting
class ProbeError(Exception):
    pass

class LoaderError(ProbeError):
    pass
         
class DriverError(ProbeError):
    pass

class ProcessorError(ProbeError):
    pass

class ProcessAbortError(ProbeError):
    pass

class ExportError(ProbeError):
    pass

class UnknowHardwareError(ProbeError):
    pass

class ConfigError(ProbeError):
    pass
    
class UserNotRootError(ProbeError):
    pass