
DEVICE_LIST = [ '/dev/ipmi0', '/dev/ipmi/0', '/dev/ipmidev/0']

'''
Set in Progress         : Set Complete
Auth Type Support       : NONE MD2 MD5 PASSWORD 
Auth Type Enable        : Callback : MD2 MD5 
                        : User     : MD2 MD5 
                        : Operator : MD2 MD5 
                        : Admin    : MD2 MD5 
                        : OEM      : MD2 MD5 
IP Address Source       : DHCP Address
IP Address              : 172.29.5.27
Subnet Mask             : 255.255.255.0
MAC Address             : 00:26:b9:33:25:d9
SNMP Community String   : public
IP Header               : TTL=0x40 Flags=0x40 Precedence=0x00 TOS=0x10
Default Gateway IP      : 172.29.5.1
Default Gateway MAC     : 00:00:00:00:00:00
Backup Gateway IP       : 0.0.0.0
Backup Gateway MAC      : 00:00:00:00:00:00
802.1q VLAN ID          : Disabled
802.1q VLAN Priority    : 0
RMCP+ Cipher Suites     : 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
Cipher Suite Priv Max   : aaaaaaaaaaaaaaa
                        :     X=Cipher Suite Unused
                        :     c=CALLBACK
                        :     u=USER
                        :     o=OPERATOR
                        :     a=ADMIN
                        :     O=OEM
'''

module Facter::Ipmi
  def self.run_ipmitool
    text = %x{ /usr/bin/ipmitool lan print }
    text.split("\n").inject(Hash.new) do |h, line|
      (l,r) = line.split(':', 2).map { |x| x.strip }
      #puts "[#{l}] [#{r}]"
      case l
      when 'IP Address' then h[:ip] = r
      when 'Subnet Mask' then h[:mask] = r
      when 'MAC Address' then h[:mac] = r
      when 'Default Gateway IP' then h[:gateway1] = r
      when 'Backup Gateway IP' then h[:gateway2] = r     
      end
      h
    end
  end
end


Facter.add(:ipmi_device) do
  setcode do
    DEVICE_LIST.any? { |x| File.exists?(x) }
  end
end

if Facter.value(:ipmi_device)   
  lan_info = Facter::Ipmi.run_ipmitool
  lan_info.each_pair do |k, v| 
    Facter.add("ipmi_#{k}") do 
      setcode do
        v
      end
    end
  end

end


