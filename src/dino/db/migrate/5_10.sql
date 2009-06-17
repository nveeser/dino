--
-- Clean Odd Values / Update values to be a little more consistent
--
DELETE property FROM property JOIN property_set ON property_set.id = property.property_set_id
	WHERE  property_set.name = "OS_codename";

DELETE property FROM property JOIN property_set ON property_set.id = property.property_set_id
	WHERE property_set.name = "NET_reserved_range";
	
DELETE FROM property_set 
	WHERE name = "OS_codename";
	
DELETE FROM property_set
	WHERE name = "NET_reserved_range";

-- Consolidate the switch and router to be the same thing
UPDATE property_set 
	SET name = CASE name
			WHEN 'HDD' 	    THEN 'hw_hdd'
			WHEN 'HW_console' THEN 'hw_console'
			WHEN 'HW_switch'  THEN 'hw_network'
			WHEN 'HW_router'  THEN 'hw_network'			
			WHEN 'HW_SUBTYPE' THEN 'hw_server'
			WHEN 'RAID_CTLR'  THEN 'hw_raidctlr'
			WHEN 'HW_pdu'     THEN 'hw_pdu'
			ELSE name 
		END;

--
-- Property
--
ALTER TABLE property
	ADD COLUMN instance_name VARCHAR(50) NOT NULL DEFAULT '1';

UPDATE property 
	SET instance_name = CONCAT('{', id, '}');

ALTER TABLE property
  	ADD UNIQUE (instance_name);


--
-- PropertyClass
--
CREATE TABLE property_class (
        id INTEGER NOT NULL AUTO_INCREMENT,
        name VARCHAR(32),
        description VARCHAR(255),
        instance_name VARCHAR(50) NOT NULL,
        PRIMARY KEY (id),
         UNIQUE (instance_name)
)ENGINE=InnoDB;


--
-- PropertySet
--
ALTER TABLE property_set 
	ADD COLUMN property_class_id INTEGER, 
	ADD COLUMN instance_name VARCHAR(50) NOT NULL DEFAULT 'temp',
	ADD CONSTRAINT property_set_property_class_id_fk FOREIGN KEY(property_class_id) REFERENCES property_class (id);

CREATE INDEX ix_property_set_property_class_id ON property_set (property_class_id);

UPDATE property_set 
	SET instance_name = CONCAT('{', id, '}'); 

ALTER TABLE property_set
	ADD UNIQUE (instance_name);


-- 
-- PropertyClassValue 
--
CREATE TABLE property_class_value (
        id INTEGER NOT NULL AUTO_INCREMENT,
        name VARCHAR(32),
        value VARCHAR(32),
        description VARCHAR(255),
        property_class_id INTEGER NOT NULL,
        instance_name VARCHAR(50) NOT NULL,
        PRIMARY KEY (id),
         UNIQUE (instance_name),
         CONSTRAINT property_class_value_property_class_id_fk FOREIGN KEY(property_class_id) REFERENCES property_class (id)
)ENGINE=InnoDB;

CREATE INDEX ix_property_class_value_property_class_id ON property_class_value (property_class_id);	


--
-- Create connection between property_class, property_set, property, and property_class_value
--

-- Populate PropertyClass names
INSERT INTO property_class (name, description, instance_name)
	SELECT DISTINCT(name) as name, NULL, name
		FROM property_set;

-- Fix keys between sets and class's, and move the value to the name
UPDATE property_set JOIN property_class ON property_set.name = property_class.name 
	SET property_set.property_class_id = property_class.id, 
		property_set.name = property_set.value, 
		property_set.value = NULL
	WHERE property_set.value IS NOT NULL;

-- A PropertySet does not have a value any more
ALTER TABLE property_set 
	DROP value;

-- Fix the names / instance_names to remove whitespace
UPDATE property_set JOIN property_class ON property_set.property_class_id = property_class.id
	SET property_set.name = REPLACE(property_set.name, " ", "_"),
		property_set.instance_name =  REPLACE(CONCAT(property_class.instance_name, '.', property_set.name), " ", "_");

UPDATE property
	JOIN property_set ON property_set.id = property.property_set_id 
	SET property.name = REPLACE(property.name, " ", "_"),
		property.instance_name =  REPLACE(CONCAT(property_set.instance_name, '.', property.name), " ", "_");


-- Add property_class_value's based on distinct class/value combinations of existing data
INSERT INTO property_class_value (name, property_class_id, instance_name)
	SELECT DISTINCT property.name, property_class.id, CONCAT(property_class.name, ".", property.name)
		FROM property
		JOIN property_set ON property_set.id = property.property_set_id 
		JOIN property_class ON  property_class.id = property_set.property_class_id;


UPDATE property_class_value JOIN property ON property_class_value.name = property.name
	SET property_class_value.description = property.description;
	
	
-- A Property gets description from the property_class_value
ALTER TABLE property 
	DROP description;
