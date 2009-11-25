'''
Example Text:

# dmidecode 2.10
SMBIOS 2.34 present.
34 structures occupying 1156 bytes.
Table at 0xBFF7B000.

Handle 0x0000, DMI type 0, 20 bytes
BIOS Information
        Vendor: Phoenix Technologies Ltd.
        Version: 2003Q2
        Release Date: 04/27/2007
        Address: 0xE5D30
        Runtime Size: 107216 bytes
        ROM Size: 1024 kB
        Characteristics:
                PCI is supported
                PNP is supported
                BIOS is upgradeable
                BIOS shadowing is allowed
                ESCD support is available
                Boot from CD is supported
                Selectable boot is supported
                EDD is supported
                5.25"/360 kB floppy services are supported (int 13h)
                5.25"/1.2 MB floppy services are supported (int 13h)
                3.5"/720 kB floppy services are supported (int 13h)
                3.5"/2.88 MB floppy services are supported (int 13h)
                Print screen service is supported (int 5h)
                8042 keyboard services are supported (int 9h)
                Serial services are supported (int 14h)
                Printer services are supported (int 17h)
                CGA/mono video services are supported (int 10h)
                ACPI is supported
                USB legacy is supported

Handle 0x0001, DMI type 1, 25 bytes
System Information
        Manufacturer: empty
        Product Name: empty
        Version: empty
        Serial Number: empty
        UUID: Not Settable
        Wake-up Type: Power Switch

Handle 0x0002, DMI type 2, 8 bytes
Base Board Information
        Manufacturer: TYAN Computer Corporation
        Product Name: S2892
        Version: empty
        Serial Number: empty

Handle 0x0003, DMI type 3, 13 bytes
Chassis Information
        Manufacturer: empty
        Type: Main Server Chassis
        Lock: Not Present
        Version: Not Specified
        Serial Number: Not Specified
        Asset Tag: Not Specified
        Boot-up State: Unknown
        Power Supply State: Unknown
        Thermal State: Unknown
        Security Status: Unknown
...

Handle 0x2600, DMI type 38, 18 bytes
IPMI Device Information
        Interface Type: KCS (Keyboard Control Style)
        Specification Version: 2.0
        I2C Slave Address: 0x10
        NV Storage Device: Not Present
        Base Address: 0x0000000000000CA8 (I/O)
        Register Spacing: 32-bit Boundaries
'''

require 'facter/util/manufacturer'
  
# Add remove things to query here
query = { 
  'Base Board Information' => [
  		{ 'Manufacturer:' => 'baseboard_manufacturer' },
	  	{ 'Product Name:' => 'baseboard_model' },
  ],
  
  'IPMI Device Information' => [ 
  		{'Specification Version:' => 'ipmi_spec_version' }, 
  ]
}

Facter::Manufacturer.dmi_find_system_info(query)

