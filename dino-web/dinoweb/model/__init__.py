from sqlalchemy import orm

import meta

def init_model(db_config):
    meta.db = db_config

    #meta.Session = orm.scoped_session(db_config.session_factory)
    meta.Session = meta.db.scoped_session_wrapper

    for entity in meta.db.entity_set:
        setattr(meta, entity.__name__, entity)
