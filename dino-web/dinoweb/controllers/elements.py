import sys
import logging

from dinoweb.lib.base import *

log = logging.getLogger(__name__)

class ElementsController(BaseController):

    def entities(self):
        c.entity_set = meta.db.entity_iterator()
        return render('/elements/entities.mako')

    def index(self, entity_name):
        entity = meta.Session().resolve_entity(entity_name)
        c.elements = meta.Session.query(entity).all()
        return render('/elements/elements.mako')

    def show(self, entity_name, id):
        entity = meta.Session().resolve_entity(entity_name)
        element = c.elements = meta.Session.query(entity).filter_by(id=id).first()
        return str(element)
