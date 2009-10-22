import sqlalchemy.exceptions as sa_exc
from sqlalchemy.util import ScopedRegistry

__all__ = [ 'make_scoped' ]

def make_scoped(object_factory, scopefunc=None, methods=(), properties=(), classmethods=()):
    # create one and see what you get.
    object_class = object_factory().__class__

    scoped_class = type("Scoped%s" % object_class.__name__, (ScopedWrapperObject,), {})

    for name in methods:
        setattr(scoped_class, name, make_registry_method(name))

    for name in properties:
        setattr(scoped_class, name, make_registry_property(name))

    for name in classmethods:
        setattr(scoped_class, name, make_registry_classmethod(name))

    return scoped_class(object_factory, scopefunc)


def make_registry_method(name):
    def do(self, *args, **kwargs):
        return getattr(self.registry(), name)(*args, **kwargs)
    return do

def make_registry_property(name):
    def set(self, attr):
        setattr(self.registry(), name, attr)
    def get(self):
        return getattr(self.registry(), name)
    return property(get, set)

def make_registry_classmethod(name):
    def do(cls, *args, **kwargs):
        return getattr(Session, name)(*args, **kwargs)
    return classmethod(do)



class ScopedWrapperObject(object):
    '''
    Wrapper for a ThreadLocal version of the object.
    '''
    def __init__(self, object_factory, scopefunc=None):
        self.object_factory = object_factory
        self.registry = ScopedRegistry(object_factory, scopefunc)

    def __call__(self, **kwargs):
        if kwargs:
            scope = kwargs.pop('scope', False)
            if scope is not None:
                if self.registry.has():
                    raise sa_exc.InvalidRequestError("Scoped session is already present; no new arguments may be specified.")
                else:
                    sess = self.session_factory(**kwargs)
                    self.registry.set(sess)
                    return sess
            else:
                return self.session_factory(**kwargs)
        else:
            return self.registry()

    def remove(self):
        if self.registry.has():
            self.registry().close()
        self.registry.clear()
