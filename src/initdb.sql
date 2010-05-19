
CREATE DATABASE IF NOT EXISTS dinodb  
	DEFAULT CHARACTER SET = UTF8;


CREATE USER 'dino-probe'@'%' 
	IDENTIFIED BY 'dino123';

GRANT SELECT, INSERT, UPDATE, DELETE 
	ON dinodb.* 
	TO 'dino-probe';


CREATE USER 'dinoadm'@'%' 
	IDENTIFIED BY 'dino123';
	
GRANT SELECT, INSERT, UPDATE, DELETE, ALTER, CREATE, INDEX
	ON dinodb.* 
	TO 'dinoadm';