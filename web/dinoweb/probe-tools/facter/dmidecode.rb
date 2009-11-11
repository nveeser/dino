if FileTest.exists?("/usr/sbin/dmidecode")
  
'''
Example Text:

Handle 0x2600, DMI type 38, 18 bytes
IPMI Device Information
        Interface Type: KCS (Keyboard Control Style)
        Specification Version: 2.0
        I2C Slave Address: 0x10
        NV Storage Device: Not Present
        Base Address: 0x0000000000000CA8 (I/O)
        Register Spacing: 32-bit Boundaries
'''
  
  # Add remove things to query here
  query = { 
    'BIOS Information' => { 
      'Vendor:' => 'bios_vendor',
    }, 
    'System Information' =>  {
      'Manufacturer:' => 'system_manufacturer',
      'Product Name:' => 'system_product_name', 
      'Serial Number:' => 'system_serial', 
      'Version:' => 'system_version',
    }, 

    'Chassis Information' => { 
      'Type:' => 'chassis_type',
    }, 
    'Processor Information' => { 
      'Version:' => 'processor_version',
      'Max Speed:' => 'processor_max_speed', 
    }, 
    'Memory Controller Information' => {
      'Maximum Memory Module Size:' => 'memory_max_module_size', 
      'Maximum Total Memory Size:' => 'memory_max_total_size',
    },
    'IPMI Device Information' => {
      'Specification Version:' => 'ipmi_spec_version',
    }
  }

  # Run dmidecode only once
  output=%x{/usr/sbin/dmidecode 2>/dev/null}

  query.each_pair do |key,subkey_map|
    subkey_map.each_pair do |subkey, name|
            
      output.split("Handle").each do |line|
        if line =~ /#{key}/  and line =~ /#{subkey} (\w.*)\n*./
          result = $1

          Facter.add("dmi_" + name) do            
            confine :kernel => :linux

            setcode do
              result
            end
          end

        end
      end
    end
  end
end
