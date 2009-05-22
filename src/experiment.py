''' Script used for experimenting with sqlalchemy features'''

import sys
import os

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__))
    
sys.path.insert(0, "/u/nicholas/mac/Documents/workspace/SQLAlchemy-0.5.3/lib/")

import sqlalchemy
from sqlalchemy import types
from sqlalchemy.orm.collections import collection 

import elixir
from elixir import Field, ManyToOne, OneToMany, ManyToMany

###############################################
#
# Example Classes 
#
__session__ = None
entity_set = __entity_collection__ = elixir.EntityCollection()
metadata = __metadata__ = sqlalchemy.schema.MetaData()

###############################################
#
# Example Classes 
#
class Person(elixir.Entity):
    elixir.using_options(tablename='person')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    name = Field(types.String(20))
    age = Field(types.Integer)
    numbers = OneToMany("PhoneNumber")


    def __str__(self):
        return "<%s %s(%s)>" % (self.__class__.__name__, self.name, self.age)
    
    
class PhoneNumber(elixir.Entity):
    elixir.using_options(tablename='address')
    elixir.using_table_options(mysql_engine='InnoDB')
    
    value1 = Field(types.String(20))
    value2 = Field(types.Integer)

    person = ManyToOne("Person")    
        
    def __str__(self):
        return "<Addr %s(%s)>" % (self.value1, self.value2)

        

#print [ "%s.%s" % (e.__module__, e.__name__) for e in entity_set ]

elixir.setup_entities(entity_set)             

def create_engine():
    from dino.config import load_config
    URI = "mysql://%(credentials)s@%(host)s/%(db)s"
    
    opts =  {
        'user' : None,
        'password' : None,
        'host' : None,
        'db' : None,
        'url' : None,
    }

    file_config = load_config("unittest.db")
    for k in opts.keys():
        # check files first    
        if file_config.has_key(k):
            opts[k] = file_config[k]
    
    opts['credentials'] = "%s:%s" % (opts['user'], opts['password'])
    
    return sqlalchemy.engine.create_engine(URI % opts, echo=False)




def stuff():   
    #db_config = DbConfig.create(file_section="unittest.db", entity_set=entity_set)
    #
    #db_config.drop_all() 
    #db_config.create_all() 
    #sess = db_config.session()
    
    e = create_engine()
    metadata.bind = e
    sess = sqlalchemy.orm.session.Session(bind=e, autocommit=True, autoflush=False, weak_identity_map=False )


    e.execute("SET FOREIGN_KEY_CHECKS = 0")
    metadata.drop_all(sess.connection())
    metadata.create_all(sess.connection())
    e.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    sess.begin()   
    print "Create Person" 
    p = Person(name="eddie", age=12) 
    sess.add(p)   
    print "Commit Person"
    sess.commit()
    
    print "------------"
    
    sess.begin()
    print "create address"
    a1 = Address(value1="Home", value2=39)
    print "add address"        
    sess.add(a1)    
    print "append address" 
    p.addresses.append(a1)      
    print "commit address"
    x = p.addresses
    print "Keys: ", x.keys()
    sess.commit()

    print "------------"

    print "Keys: ", p.addresses.keys()

    sess.begin()
    print "create address"
    a2 = Address(value1="Work", value2=30)                
    print "add address"        
    sess.add(a2)    
    print "append address" 
    p.addresses.append(a2)
    print "Keys: ", p.addresses.keys()
    
    print "commit address"
    sess.commit()

    print "------------"

    print "Keys: ", p.addresses.keys()

    
    p = sess.query(Person).filter_by(name='eddie').first()

    for k in p.addresses.keys():
        print "Key: %s" % k
        


    

def stuff2():
    from dino.db.dbconfig import DbConfig
    from dino.db.schema import *
    
    db = DbConfig.create(file_section="unittest.db")
    print "Create/Drop"
    db.drop_all()
    db.create_all()
    session = db.session()
    
    session.begin()
    s = Site(name='sjc1', address1="", address2="", city="", state="", postal="", description="")   
    r = Rack(name="1.10", site=s)
    session.add(r) 
    c = Chassis(name='small', vendor='yourmom', product='yourmom', racksize=1)
    session.add(c)
    print "Commit Chassis, Rack, Site"
    session.commit()

    
    session.begin()
    
    d = Device(status="INVENTORY", hid="001EC943AF41", rackpos=13, rack=r,  chassis=c, serialno='..CN7082184700NF.',
        hw_type="util-6", pdu_port=0, pdu_module=None )
    p1 = Port(name="eth0", mac="03:03:03:03:00:01", device=d, vlan=10, is_ipmi=None, is_blessed=True)    
    p2 = Port(name="eth1", mac="03:03:03:03:00:02", device=d, vlan=None, is_ipmi=True, is_blessed=None)
    session.add(d)

    print "Commit Device/Port/Port"
    session.commit()
    
        
if __name__ == "__main__":
    stuff2()
        
