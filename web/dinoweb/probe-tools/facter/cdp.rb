
require 'facter/util/ip'

CACHE_DIR="/var/tmp"
CACHE_TIMEOUT = 60*100 # 100 min

module Facter::Cdp
  SWITCH_RE = /.*Device ID\s+value:\s+(\S+)\s.*/m
  PORT_RE = /.*Port ID\s+value:\s+(\S+)\s.*/m

  def self.run_cdp(cache_file, iface)
      cmd = "/usr/bin/cdpr -t 70 -d #{iface} > #{cache_file} 2> /dev/null"      
      if not system(cmd)
          raise "Cannot execute cdp: #{cmd}"
      end
  end
    
  def self.get_cdp(iface)
    if Process.uid != 0
      return nil
    end
    
    if not File.directory?(CACHE_DIR)
      return nil
    end
    
    cache_file = "#{CACHE_DIR}/cdp_#{iface}"

    if File.exists?(cache_file)
      if Time.now - File.mtime(cache_file) > CACHE_TIMEOUT
        self.run_cdp(cache_file, iface)
      end
    else
      self.run_cdp(cache_file, iface)
    end
    IO.read(cache_file)
  end

end

Facter.value(:interfaces).split(',').each do |iface|
  if not Facter.value("ipaddress_#{iface}").nil?
    Facter.add("cdp_device_" + Facter::Util::IP.alphafy(iface)) do
      setcode do
        output = Facter::Cdp.get_cdp(iface)
        if not output.nil?
          m = Facter::Cdp::SWITCH_RE.match(output)
          if not m.nil?
            m[1].to_s
          end
        end        
      end
    end

    Facter.add("cdp_port_" + Facter::Util::IP.alphafy(iface)) do
      setcode do
        output = Facter::Cdp.get_cdp(iface)
        if not output.nil?
          m = Facter::Cdp::PORT_RE.match(output)
          if not m.nil?
            m[1].to_s
          end
        end
      end
    end
  end  
end

