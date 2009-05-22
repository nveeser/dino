


CREATE TABLE dictionary (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(32) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	label VARCHAR(32) NOT NULL, 
	parent_id INTEGER, 
	order_num INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	 CONSTRAINT dictionary_parent_id FOREIGN KEY(parent_id) REFERENCES dictionary (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_dictionary_name ON dictionary (name);

CREATE TABLE os (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	os_dict INTEGER, 
	distro_ver VARCHAR(128) NOT NULL, 
	kernel_ver VARCHAR(128) NOT NULL, 
	parent_id INTEGER, 
	is_deprecated BOOL NOT NULL, 
	is_rapids BOOL NOT NULL, 
	order_num INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT os_os_dict FOREIGN KEY(os_dict) REFERENCES dictionary (id), 
	 CONSTRAINT os_parent_id FOREIGN KEY(parent_id) REFERENCES os (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_os_kernel_ver ON os (kernel_ver);

CREATE TABLE company (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(32) NOT NULL, 
	description VARCHAR(64) NOT NULL, 
	company_dict INTEGER, 
	parent_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT company_company_dict FOREIGN KEY(company_dict) REFERENCES dictionary (id), 
	 FOREIGN KEY(parent_id) REFERENCES company (id)
)ENGINE=InnoDB

;

CREATE TABLE site (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(32) NOT NULL, 
	is_active BOOL NOT NULL, 
	domain VARCHAR(64) NOT NULL, 
	address1 VARCHAR(80) NOT NULL, 
	address2 VARCHAR(80) NOT NULL, 
	city VARCHAR(64) NOT NULL, 
	state VARCHAR(2) NOT NULL, 
	postal VARCHAR(16) NOT NULL, 
	company_id INTEGER, 
	description VARCHAR(255) NOT NULL, 
	parent_id INTEGER, 
	ownership VARCHAR(16), 
	geo_lat FLOAT(10), 
	geo_long FLOAT(10), 
	sitetype VARCHAR(10), 
	timezone VARCHAR(4), 
	PRIMARY KEY (id), 
	 CONSTRAINT site_company_id FOREIGN KEY(company_id) REFERENCES company (id), 
	 CONSTRAINT site_parent_id FOREIGN KEY(parent_id) REFERENCES site (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_site_name ON site (name);

CREATE TABLE model (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(128) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	max FLOAT(10) NOT NULL, 
	min FLOAT(10) NOT NULL, 
	racksize VARCHAR(8), 
	is_qualified BOOL NOT NULL, 
	company_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT model_company_id FOREIGN KEY(company_id) REFERENCES company (id)
)ENGINE=InnoDB

;

CREATE TABLE appliance (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name TEXT(64), 
	description TEXT, 
	PRIMARY KEY (id)
)ENGINE=InnoDB

;

CREATE TABLE pod (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(128) NOT NULL, 
	domain VARCHAR(32), 
	is_partner BOOL NOT NULL, 
	PRIMARY KEY (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_pod_domain ON pod (domain);
CREATE INDEX ix_pod_name ON pod (name);

CREATE TABLE transaction (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	committed DATETIME, 
	created DATETIME, 
	author VARCHAR(15), 
	PRIMARY KEY (id)
)ENGINE=InnoDB

;

CREATE TABLE supernet (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	handle VARCHAR(32) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(256) NOT NULL, 
	addr INTEGER UNSIGNED, 
	addr_last INTEGER UNSIGNED, 
	mask INTEGER NOT NULL, 
	company_id INTEGER, 
	org_company_id INTEGER, 
	is_assigned BOOL NOT NULL, 
	is_active BOOL NOT NULL, 
	acquired_time INTEGER, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT supernet_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 CONSTRAINT supernet_company_id FOREIGN KEY(company_id) REFERENCES company (id), 
	 CONSTRAINT supernet_org_company_id FOREIGN KEY(org_company_id) REFERENCES company (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_supernet_addr ON supernet (addr);
CREATE INDEX ix_supernet_handle ON supernet (handle);
CREATE INDEX ix_supernet_addr_last ON supernet (addr_last);

CREATE TABLE subnet (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	addr INTEGER UNSIGNED NOT NULL, 
	addr_last INTEGER UNSIGNED NOT NULL, 
	mask INTEGER NOT NULL, 
	parent_id INTEGER, 
	supernet_id INTEGER, 
	site_id INTEGER, 
	pod_id INTEGER, 
	vlan INTEGER NOT NULL, 
	description VARCHAR(256) NOT NULL, 
	is_assigned BOOL NOT NULL, 
	is_active BOOL NOT NULL, 
	is_console BOOL NOT NULL, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT subnet_parent_id FOREIGN KEY(parent_id) REFERENCES subnet (id), 
	 CONSTRAINT subnet_supernet_id FOREIGN KEY(supernet_id) REFERENCES supernet (id), 
	 CONSTRAINT subnet_pod_id FOREIGN KEY(pod_id) REFERENCES pod (id), 
	 CONSTRAINT subnet_site_id FOREIGN KEY(site_id) REFERENCES site (id), 
	 CONSTRAINT subnet_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_subnet_addr_last ON subnet (addr_last);
CREATE INDEX ix_subnet_addr ON subnet (addr);

CREATE TABLE `subnetStat` (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	subnet_id INTEGER, 
	total INTEGER NOT NULL, 
	up INTEGER NOT NULL, 
	ch_ip INTEGER NOT NULL, 
	active INTEGER NOT NULL, 
	assigned INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	 CONSTRAINT subetstat_subnet_id FOREIGN KEY(subnet_id) REFERENCES subnet (id)
)ENGINE=InnoDB

;

CREATE TABLE `range` (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	subnet_id INTEGER, 
	addr INTEGER UNSIGNED, 
	addr_last INTEGER UNSIGNED, 
	description VARCHAR(256) NOT NULL, 
	is_active BOOL NOT NULL, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT range_subnet_id FOREIGN KEY(subnet_id) REFERENCES subnet (id), 
	 CONSTRAINT range_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id)
)ENGINE=InnoDB

;

CREATE TABLE `subnetDetail` (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	subnet_id INTEGER, 
	subnet_dict INTEGER, 
	note TEXT NOT NULL, 
	PRIMARY KEY (id), 
	 CONSTRAINT subnetdetail_subnet_id FOREIGN KEY(subnet_id) REFERENCES subnet (id), 
	 CONSTRAINT subnetdetail_subnet_dict FOREIGN KEY(subnet_dict) REFERENCES dictionary (id)
)ENGINE=InnoDB

;

CREATE TABLE hnode (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	handle VARCHAR(128), 
	mw_tag INTEGER, 
	type_dict INTEGER, 
	status VARCHAR(32), 
	parent_id INTEGER, 
	pod_id INTEGER, 
	os_id INTEGER, 
	site_id INTEGER, 
	coreswitch VARCHAR(2) NOT NULL, 
	model_id INTEGER, 
	serialno VARCHAR(32) NOT NULL, 
	loc_row INTEGER, 
	loc_rack INTEGER, 
	loc_side VARCHAR(2), 
	loc_rackpos INTEGER, 
	notes TEXT NOT NULL, 
	transaction_id INTEGER, 
	acct_tag VARCHAR(64), 
	vendor_tag VARCHAR(64), 
	date_acquired DATETIME, 
	pdu_id INTEGER, 
	pdu_module VARCHAR(16), 
	pdu_port VARCHAR(32), 
	console_id INTEGER, 
	console_port VARCHAR(16), 
	PRIMARY KEY (id), 
	 CONSTRAINT hnode_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 CONSTRAINT hnode_model_id FOREIGN KEY(model_id) REFERENCES model (id), 
	 CONSTRAINT hnode_pod_id FOREIGN KEY(pod_id) REFERENCES pod (id), 
	 CONSTRAINT hnode_pdu_id FOREIGN KEY(pdu_id) REFERENCES hnode (id), 
	 CONSTRAINT hnode_type_dict FOREIGN KEY(type_dict) REFERENCES dictionary (id), 
	 CONSTRAINT hnode_parent_id FOREIGN KEY(parent_id) REFERENCES hnode (id), 
	 CONSTRAINT hnode_os_id FOREIGN KEY(os_id) REFERENCES os (id), 
	 CONSTRAINT hnode_site_id FOREIGN KEY(site_id) REFERENCES site (id), 
	 CONSTRAINT hnode_console_id FOREIGN KEY(console_id) REFERENCES hnode (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_hnode_mw_tag ON hnode (mw_tag);
CREATE INDEX ix_hnode_handle ON hnode (handle);

CREATE TABLE mac_port (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	hnode_id INTEGER, 
	ifindex VARCHAR(32) NOT NULL, 
	ifname VARCHAR(64) NOT NULL, 
	mac VARCHAR(64) NOT NULL, 
	vlan INTEGER NOT NULL, 
	parent_id INTEGER, 
	is_bonded BOOL NOT NULL, 
	is_stale BOOL NOT NULL, 
	is_blessed BOOL NOT NULL, 
	is_ipmi BOOL NOT NULL, 
	s_port INTEGER, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT mac_port_hnode_id FOREIGN KEY(hnode_id) REFERENCES hnode (id), 
	 CONSTRAINT mac_port_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 CONSTRAINT mac_port_parent_id FOREIGN KEY(parent_id) REFERENCES mac_port (id), 
	 CONSTRAINT mac_port_s_port FOREIGN KEY(s_port) REFERENCES mac_port (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_mac_port_mac ON mac_port (mac);

CREATE TABLE ip_mac (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	site_id INTEGER, 
	parent_id INTEGER, 
	addr INTEGER UNSIGNED, 
	mac_port_id INTEGER, 
	hnode_id INTEGER, 
	is_stale BOOL, 
	`is_VSI` BOOL, 
	is_dhcp BOOL, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT ip_mac_mac_port_id FOREIGN KEY(mac_port_id) REFERENCES mac_port (id), 
	 CONSTRAINT ip_mac_site_id FOREIGN KEY(site_id) REFERENCES site (id), 
	 CONSTRAINT ip_mac_hnode_id FOREIGN KEY(hnode_id) REFERENCES hnode (id), 
	 CONSTRAINT ip_mac_parent_id FOREIGN KEY(parent_id) REFERENCES ip_mac (id), 
	 CONSTRAINT ip_mac_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_ip_mac_addr ON ip_mac (addr);

CREATE TABLE name_ip (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255), 
	ip_mac_id INTEGER, 
	pod_id INTEGER, 
	site_id INTEGER, 
	hnode_id INTEGER, 
	is_stale BOOL, 
	`A_record_only` BOOL, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT name_ip_hnode_id FOREIGN KEY(hnode_id) REFERENCES hnode (id), 
	 CONSTRAINT name_ip_site_id FOREIGN KEY(site_id) REFERENCES site (id), 
	 CONSTRAINT name_ip_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 FOREIGN KEY(ip_mac_id) REFERENCES ip_mac (id), 
	 CONSTRAINT name_ip_pode_id FOREIGN KEY(pod_id) REFERENCES pod (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_name_ip_name ON name_ip (name);

CREATE TABLE interface (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	parent_id INTEGER, 
	subnet_id INTEGER, 
	hnode_id INTEGER, 
	`ifName` VARCHAR(64) NOT NULL, 
	`ifType` INTEGER NOT NULL, 
	`ifDescr` VARCHAR(256) NOT NULL, 
	`ifIndex` INTEGER NOT NULL, 
	`ifSpeed` INTEGER NOT NULL, 
	`ifPhysAddr` VARCHAR(64) NOT NULL, 
	`ifOperStatus` VARCHAR(32) NOT NULL, 
	`ifAdminStatus` VARCHAR(32) NOT NULL, 
	`ifLastChange` INTEGER NOT NULL, 
	`portDuplex` VARCHAR(32) NOT NULL, 
	mac_ip_id INTEGER, 
	s_time INTEGER, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 FOREIGN KEY(parent_id) REFERENCES interface (id), 
	 FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 FOREIGN KEY(subnet_id) REFERENCES subnet (id), 
	 FOREIGN KEY(hnode_id) REFERENCES hnode (id)
)ENGINE=InnoDB

;

CREATE TABLE circuit (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	info VARCHAR(256) NOT NULL, 
	`use` VARCHAR(32) NOT NULL, 
	site_id INTEGER, 
	term_site_id INTEGER, 
	interface_id INTEGER, 
	term_interface_id INTEGER, 
	carrier_company_id INTEGER, 
	carrier_ident VARCHAR(64) NOT NULL, 
	provider_company_id INTEGER, 
	provider_ident VARCHAR(64) NOT NULL, 
	parent_id INTEGER, 
	ownership VARCHAR(32) NOT NULL, 
	s_time INTEGER, 
	term_s_time INTEGER, 
	notes TEXT NOT NULL, 
	is_stale BOOL NOT NULL, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 FOREIGN KEY(term_site_id) REFERENCES site (id), 
	 CONSTRAINT circuit_site_id FOREIGN KEY(site_id) REFERENCES site (id), 
	 FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 FOREIGN KEY(interface_id) REFERENCES interface (id), 
	 FOREIGN KEY(term_interface_id) REFERENCES interface (id), 
	 FOREIGN KEY(carrier_company_id) REFERENCES company (id), 
	 FOREIGN KEY(provider_company_id) REFERENCES company (id), 
	 FOREIGN KEY(parent_id) REFERENCES circuit (id)
)ENGINE=InnoDB

;

CREATE TABLE hdd (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	hnode_id INTEGER, 
	name VARCHAR(255), 
	controller_dict INTEGER, 
	hdtype_dict INTEGER, 
	hd_pos INTEGER, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT hdd_hnode_id FOREIGN KEY(hnode_id) REFERENCES hnode (id), 
	 CONSTRAINT hdd_controller_dict FOREIGN KEY(controller_dict) REFERENCES dictionary (id), 
	 CONSTRAINT hdd_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 CONSTRAINT hdd_hdtype_dict FOREIGN KEY(hdtype_dict) REFERENCES dictionary (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_hdd_id ON hdd (id);

CREATE TABLE `key` (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	handle VARCHAR(128), 
	ssh_rsa_key TEXT, 
	ssh_rsa_pub TEXT, 
	ssh_dsa_key TEXT, 
	ssh_dsa_pub TEXT, 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT key_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id)
)ENGINE=InnoDB

;
CREATE INDEX ix_key_handle ON `key` (handle);

CREATE TABLE rapids (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	hnode_id INTEGER, 
	appliance_id INTEGER, 
	key_id INTEGER, 
	rapids_ver INTEGER, 
	build_type VARCHAR(32), 
	build_tag VARCHAR(32), 
	bootimg VARCHAR(32), 
	transaction_id INTEGER, 
	PRIMARY KEY (id), 
	 CONSTRAINT rapids_hnode_id FOREIGN KEY(hnode_id) REFERENCES hnode (id), 
	 CONSTRAINT rapids_key_id FOREIGN KEY(key_id) REFERENCES `key` (id), 
	 CONSTRAINT rapids_transaction_id FOREIGN KEY(transaction_id) REFERENCES transaction (id), 
	 CONSTRAINT rapids_appliance_id FOREIGN KEY(appliance_id) REFERENCES appliance (id)
)ENGINE=InnoDB

;

