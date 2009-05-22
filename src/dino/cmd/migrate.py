import os
import logging
from optparse import Option

from dino.config import load_config

from dino.cmd.command import with_session
from dino.cmd.maincmd import MainCommand

from dino.db import schema, DbConfig

os_app_list = (
("baccus-postgis", "baccus-blog" ),
("baccus-postgis", "baccus-build" ),
("baccus-postgis", "baccus-dev" ),
("baccus-postgis", "baccus-ops" ),
("baccus-postgis", "baccus-prod" ),
("baccus-postgis", "baccus-seed" ),
("baccus-postgis", "mwdeploy" ),
("baccus-postgis", "mwdeploy-postgis" ),
("baccus-postgis", "postgis" ),
("baccus", "baccus-blog" ),
("baccus", "baccus-build" ),
("baccus", "baccus-dev" ),
("baccus", "baccus-hadoop" ),
("baccus", "baccus-ops" ),
("baccus", "baccus-prod" ),
("baccus", "baccus-seed" ),
("baccus", "mwdeploy" ),
("chronos", "baccus-blog" ),
("chronos", "baccus-build" ),
("chronos", "baccus-dev" ),
("chronos", "baccus-hadoop" ),
("chronos", "baccus-ops" ),
("chronos", "baccus-prod" ),
("chronos", "baccus-seed" ),
("chronos", "mwdeploy" ),
("chronos", "mwdeploy-postgis" ),
("chronos", "postgis" ),

# Random OS/App types I am not sure when to get rid of...
("ONTAP","non-rapids"),
("RHEL52","non-rapids"),
("baccus-postgis","baccus-mwdeploy"),
("discover","baccus-mwdeploy"),
("discover","baccus-prod"),
("discover","mwdeploy"),
("legacy","dev-generic-2"),
("starscream","dev-generic-070101"),
("starscream","prod-generic-megatron"),
("starscream","starscream_ops"),
("unknown","non-rapids"),
)




 
class MigrateCommand(MainCommand):
    ''' Create new database instance and migrate data from old instance specified by src_schema '''
    
    NAME = 'migrate'
    USAGE = '''[ -s <source_url> ] 
               [ -i|--import-dir <import-dir> ] 
               [ -p|--special-dir <special-dir> ]'''
    GROUP = "system"    
    OPTIONS = ( 
        Option('-s', '--src', dest='source_url', default=None),  
        Option('-i', '--import-dir', dest='import_dir', default=None),
        Option('-p', '--special-dir', dest='special_dir', default=None),
        Option('--no-import', dest='doimport', action='store_false', default=True),
        Option('--cleardb', dest='cleardb', action='store_true', default=True),
    )

    
        
    @with_session
    def execute(self, session): 
        self.settings = load_config("migrate") 

        special_dir = self.option.special_dir or self.settings.special_dir
        import_dir = self.option.import_dir or self.settings.import_dir
        source_url = self.option.source_url or self.settings.source_url
        
        src_db = DbConfig(url=self.settings.src_uri)        
        src_conn = src_db.connection()  
        
        self.db_config.assert_unprotected()
        
        if self.option.cleardb:
            self.clear_schema(session)
        
        self.split_property_tables(session, src_conn)
        
        self.add_os_appliance(session)
        
        self.copy_sitepod(session, src_conn)
                
        self.create_rack(session)
        
        self.copy_subnets(session, src_conn)

        self.add_new_subnets(session, src_conn)
        
        self.copy_chassis(session, src_conn)
       
        # first import special devices, since
        # they are used in server imports.
        if self.option.doimport:                
            if special_dir is not None and special_dir != "":
                self.run_import_hosts(special_dir)
    
            if import_dir is not None and import_dir != "":
                self.run_import_hosts(import_dir)
    
            self.copy_ssh_keys(session, src_conn)

        src_conn.close()
        
    
    def clear_schema(self, session):
        self.log.info( "--------- [ Empty schema and create tables ] --------")        
        self.db_config.drop_all()                
        self.db_config.create_all()
    
    
    def split_property_tables(self, session, src_conn):
              
        dest_schema = self.db_config.db
        
        self.log.info( "--------- [ Update Property Tables] --------")
        
        set_select = """ 
            SELECT  id, name, description as value, label as description 
                FROM dictionary
                WHERE parent_id IS NULL"""
            
        prop_select = """
            SELECT  id, name, description as value, label as description, parent_id as set_id
                FROM dictionary    
                WHERE parent_id IS NOT NULL
            """
            
        session.begin()
        
        map = {}
        result = src_conn.execute(set_select)
        for row in result:
            d = dict([ (str(n), v) for n,v in row.items() ])
            s = schema.PropertySet(**d)
            map[s.id] = s 
            self.log.fine(" Adding: PropertySet:%s" % s.name)
            session.add(s)
        
        result = src_conn.execute(prop_select)
        for row in result: 
            d = dict([ (str(n), v) for n,v in row.items() ]) 
            p = schema.Property(**d)
            p.property_set = map[p.set_id]
            session.add(p)

        size = len(session.new) 
        session.commit()
        self.log.info("Committed Objects: %d", size)       
    
    
    def add_os_appliance(self, session):
        self.log.info( "--------- [ Add OS/Appliance ] --------")
        session.begin()
            
        map = {}
        for (osname,app) in os_app_list:
            if map.has_key(osname):
                os = map[osname]
            else:
                os = session.query(schema.OperatingSystem).filter_by(name=osname).first()
                
            if os is None:
                self.log.fine("adding new OS: " + osname)
                os = schema.OperatingSystem(name=osname)
                map[osname] = os
                
            self.log.fine("Adding: " + app)
            app = schema.Appliance(name=app, os=os)
            session.add(app)
        
        size = len(session.new) 
        session.commit()
        self.log.info("Committed Objects: %d", size)       
    

    def copy_sitepod(self, session, src_conn):
        self.log.info( "--------- [ Copy Site/Pod data ] --------")
        session.begin()
        self.site_map = {}
        
        for r in src_conn.execute('SELECT * FROM site order by id'):
            site = self._copy_attributes(schema.Site(), r, ('name', 'is_active', 'address1','address2', 'city', 'state', 'postal', 'description','sitetype', 'timezone'))
            self.log.fine("Adding: " + site.name)
            session.add(site)
            self.site_map[r['id']] = site

        # add 631h by hand
        site = schema.Site(name='631h', 
	                  is_active=1, 
			  address1='631 Howard Street',
			  address2='Suite 400', 
			  city='San Francisco', 
			  state='CA', 
			  postal='94105', 
			  description='SF Corporate Office', 
			  sitetype='corp', 
			  timezone='PST')
        self.log.fine("Adding: " + site.name)
        session.add(site)
        
        self.pod_map = {}
        
        for r in src_conn.execute('SELECT * FROM pod'):
            pod = schema.Pod()
            pod.name = r['domain']
            pod.description = r['description']
            self.log.fine("Adding: " + pod.name)
            session.add(pod)
            self.pod_map[r['id']] = pod
            
        size = len(session.new) 
        session.commit()
        self.log.info("Committed Objects: %d", size)       


    def create_rack(self, session):
        ''' Seed the rack info for sjc1 and 631h.''' 
        self.log.info( "--------- [ Add Rack data ] --------")
        session.open_changeset()

        # sjc1
        site = session.query(schema.Site).filter_by(name='sjc1').first()
        for rnum in range(1, 6):
            rack_name = '1.' + str(rnum)
            rack = schema.Rack(name=rack_name, site=site, location='corp net')
            session.add(rack)
            
        for rnum in range(6, 12):
            rack_name = '1.' + str(rnum)
            rack = schema.Rack(name=rack_name, site=site, location='prod net')
            session.add(rack)
    
        # 631h, row1
        site = session.query(schema.Site).filter_by(name='631h').first()
        for rnum in range(1,4):
            rack_name = '1.' + str(rnum)
            rack = schema.Rack(name=rack_name, site=site, size=45, location='office closet')
            session.add(rack)
            
        # 631h, row2
        rack = schema.Rack(name='2.2', site=site, size=48, location='office closet')
        session.add(rack)
    
        cs = session.submit_changeset()
        self.log.info("Committed Changeset: " + str(cs))       
        
    def copy_subnets(self, session, src_conn):
        self.log.info("--------- [ Copy Subnet/Supernet data ] --------")
        session.open_changeset()
    
        self.supernet_map = {}
        for r in src_conn.execute('SELECT * FROM supernet'):
            addr = schema.IpType.ntoa(r['addr'])
            length = r['mask']  
            s = schema.Subnet(addr=addr, mask_len=length)
            s = self._copy_attributes(s, r, ('is_assigned', 'is_active'))        
            s.admin_info = self._copy_attributes(schema.SubnetAdminInfo(), r, ('acquired_time',))        
            
            self.supernet_map[r['id']] = s
            self.log.fine("Adding: " + str(s))        
            session.add(s)
       
        
        self.subnet_map = {}
        for r in src_conn.execute('SELECT * FROM subnet order by parent_id'):
            addr = schema.IpType.ntoa(r['addr'])
            length = r['mask']  
            s = schema.Subnet(addr=addr, mask_len=length)            
            s = self._copy_attributes(s, r, ('is_active', 'is_console', 'is_assigned', 'description'))

            if r['parent_id'] is not None:
                s.parent = self.subnet_map[r['parent_id']]
            
            if r['supernet_id'] is not None:
                s.parent = self.supernet_map[r['supernet_id']]
            
            if r['site_id'] is not None:
                s.site = self.site_map[r['site_id']]
                
            self.subnet_map[r['id']] = s
            self.log.fine("Adding: " + str(s))
            session.add(s)


        for r in src_conn.execute('SELECT * FROM range'):        
            if r['subnet_id'] is not None:
                subnet = self.subnet_map[r['subnet_id']]
            else:
                self.log.error("Range does not have a parent subnet: %s" % r )
                continue
                                
            start = r['addr'] - subnet.naddr
            end = r['addr_last'] - subnet.naddr
            
            range = schema.Range(subnet=subnet, start=start, end=end, range_type='dhcp')            
            range.description = r['description']
            self.log.fine("Adding: " + str(range))
            session.add(range)
            
            range = schema.Range(subnet=subnet, start=1, end=10, range_type='policy')
            self.log.fine("Adding: " + str(range))
            session.add(range)
            
        cs = session.submit_changeset()
        self.log.info("Committed Changeset: " + str(cs))


    def add_new_subnets(self, session, src_conn):

        self.log.info("--------- [ Copy Subnet/Supernet data ] --------")
        session.open_changeset()

        # Add a few more subnets
        site   = session.query(schema.Site).filter_by(instance_name='sjc1').first()
        #parent = session.query(schema.Subnet).filter_by(instance_name='172.29.0.0_16').first()
        parent = None
        slash_24s = ['172.29.253.0','172.29.250.0','172.29.254.0','172.29.255.0', 
                    '10.2.254.0', '10.2.255.0']
        for n in slash_24s:
            s = schema.Subnet(addr=str(schema.IpType.aton(n)), 
                         mask_len=24, is_assigned=1, is_active=1, 
                         is_console=0, parent=parent, site=site)
            self.log.fine("Adding: " + str(s))
            session.add(s)
        
        slash_23s = ['172.29.248.0', '10.2.250.0']
        for n in slash_23s:
            s = schema.Subnet(addr=str(schema.IpType.aton(n)), 
                         mask_len=23, is_assigned=1, is_active=1, 
                         is_console=0, parent=parent, site=site)
            self.log.fine("Adding: " + str(s))
            session.add(s)

        cs = session.submit_changeset()
        self.log.info("Committed Changeset: " + str(cs))
        
    def run_import_hosts(self, d):
        
        files = [ os.path.join(d, f) for f in os.listdir(d) if f != ".svn" ]
        
        imp_cmd_cls = MainCommand.get_command('jsonimport')
        imp_cmd = imp_cmd_cls(self.db_config, self.cli)  
        imp_cmd.parse(files) 
        l = imp_cmd.execute()
        
        
        
        
    def copy_chassis(self, session, src_conn):
        self.log.info( "--------- [ Copy Site/Pod data ] --------")
        session.open_changeset()
        
        for r in src_conn.execute('SELECT * FROM model'):
            inst = self._copy_attributes(schema.Chassis(), r, ('name', 'description', 'racksize'))
            inst.vendor = "UNKNOWN"
            inst.product = "UNKNOWN"
            self.log.fine("Adding: " + inst.name)
            session.add(inst)
       
        # add a few more, for routers and switches.
        chassis = schema.Chassis(name='cisco-4948', vendor='cisco', product='cisco-4948', description='switch hardware', racksize='1')
        session.add(chassis)
        chassis = schema.Chassis(name='cisco-7604', vendor='cisco', product='cisco-7604', description='router hardware', racksize='4')
        session.add(chassis)
        chassis = schema.Chassis(name='cisco-6506', vendor='cisco', product='cisco-6506', description='switch hardware', racksize='8')
        session.add(chassis)
        chassis = schema.Chassis(name='lx-4032', vendor='cisco', product='lx-4032', description='console unit', racksize='1')
        session.add(chassis)
        chassis = schema.Chassis(name='lx-4048', vendor='cisco', product='lx-4048', description='console unit', racksize='1')
        session.add(chassis)
        chassis = schema.Chassis(name='cs-48vd', vendor='sentry', product='Sentry CDU', description='pdu unit', racksize='0')
        session.add(chassis)
        
        cs = session.submit_changeset()
        self.log.info("Committed Changeset: " + str(cs))
        

        
    @staticmethod        
    def _copy_attributes(entity, row, attrs):
        for a in attrs:
            setattr(entity, a, row[a])
        return entity
    

        
    def copy_ssh_keys(self, session, src_conn):
        
        stmt = '''
        SELECT ssh_rsa_key as rsa_key, ssh_rsa_pub as rsa_pub, ssh_dsa_key as dsa_key, ssh_dsa_pub as dsa_pub 
        FROM `key` 
        WHERE handle LIKE '%s%%%%' 
        ORDER BY transaction_id DESC 
        LIMIT 1
        '''
        session.open_changeset()
        
        for host in session.query(schema.Host).filter_by(ssh_key_info=None).all():
            self.log.fine("Finding HostKey info for: %s", host)
            
            
            row = src_conn.execute(stmt % host.hostname()).fetchone()
            if row:
                self.log.info("   Updating: %s" , host)                                
                d = dict([ (str(n), v) for n,v in row.items() ])
                host.ssh_key_info = schema.SshKeyInfo(**d)
            else:
                self.log.warning("  No Keys found for Host: %s", host)
            
        
        if len(session.dirty) > 0:
            cs = session.submit_changeset()
            self.log.info("Committed Changeset: " + str(cs))
