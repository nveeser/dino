import sys
import logging

import sqlalchemy.orm.properties as sa_props

from dinoweb.lib.base import *

log = logging.getLogger(__name__)

class ElementsController(BaseController):

    def entities(self):
        from dino.db.element import Element
        def entity_generator():
            for i, e in enumerate(meta.db.entity_iterator()):
                name = str(e)
                is_element = issubclass(e, Element)
                is_revisioned = issubclass(e, Element) and e.has_revision_entity()
                yield (i, name, is_element, is_revisioned)

        c.entity_data = entity_generator()
        return render('/elements/entities.mako')

    def _get_column_names(self, entity):
        ignore_names = ('revision', 'changeset', 'instance_name', 'id')

        props = list(entity.mapper.iterate_properties)
        all_col_names = [ p.key for p in props
            if isinstance(p, sa_props.ColumnProperty) and p.key not in ignore_names]

        all_rel_names = [p.key for p in props if isinstance(p, sa_props.RelationProperty)]

        col_names = [n for n in all_col_names
                                if not (n.endswith("_id") and n[:-3] in all_rel_names)]

        rel_names = [ n for n in all_rel_names if n not in ignore_names ]

        if entity.has_revision_entity():
            col_names = ['revision', 'changeset'] + col_names

        return col_names + rel_names

    def index(self, entity_name):
        entity = meta.Session().resolve_entity(entity_name)

        c.element_prop_names = self._get_column_names(entity)

        def element_generator():
            for e in meta.Session.query(entity).all():
                values = tuple(getattr(e, n) for n in c.element_prop_names)
                yield (e.id, e,) + values

        c.element_data = element_generator()
        return render('/elements/elements.mako')

    def show(self, entity_name, id):
        entity = meta.Session().resolve_entity(entity_name)
        names = self._get_column_names(entity)

        element = meta.Session.query(entity).filter_by(id=id).first()

        def generator():
            yield ("ElementName", element.element_name)
            for name in names:
                yield (name, getattr(element, name))

        c.element_data = generator()
        return render('/elements/element.mako')
