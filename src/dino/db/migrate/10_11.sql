
ALTER TABLE device
	MODIFY COLUMN switch_port VARCHAR(32);
ALTER TABLE device_revision
	MODIFY COLUMN switch_port VARCHAR(32);
	
# Go ahead and make instance_name something large	
ALTER TABLE appliance
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE chassis
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE device
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE device_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE dns_record
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE dns_record_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE host
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE host_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE interface
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE interface_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE ip
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE ip_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE os
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE pod
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE port
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE port_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE property
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE property_class
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE property_class_value
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE property_set
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE rack
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE rack_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE range
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE range_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE site
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE ssh_key_info
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE ssh_key_info_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE subnet
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE subnet_admin_info
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE subnet_admin_info_revision
	MODIFY COLUMN instance_name VARCHAR(100);
ALTER TABLE subnet_revision
	MODIFY COLUMN instance_name VARCHAR(100);
