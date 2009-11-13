from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.command import *
from dino.db import *


class GardenCommand(DinoCommand):
    '''
    Process all Device / Host objects, and update any missing fields by info or by convention.
    '''
    NAME = 'garden'
    USAGE = ''
    GROUP = 'data'
    OPTIONS = (
         Option('-n', '--no-submit', action='store_false', dest='submit', default=True),
    )

    @with_session
    def execute(self, opts, args, session):
        self.avail_ip_map = {}

        session.begin()

        self.log.info("Looking for IPMI ports")
        for port in session.query(Port).filter_by(is_ipmi=True):
            if port.interface is not None:
                self.update_ipmi_interface(port.interface)

        self.update_addresses(session)

        desc = session.create_change_description()
        if len(desc) > 0:
            self.log.info("Pending Changes:")
            for change in desc:
                self.log.info("  " + str(change))


        if opts.submit:
            self.log.fine("Submitting Objects: %s / %s " % (len(session.new), len(session.dirty)))
            cs = session.submit_changeset()
            self.log.info("Committed Changeset: " + str(cs))

        else:
            session.revert_changeset()
            self.log.info("Not submitting")



    def update_addresses(self, session):
        self.log.info("Update Subnet Information")
        for addr in session.query(IpAddress).all():
            subnet = addr.query_subnet()
            if addr.subnet != subnet:
                self.log.info("  Updating: %s", str(addr))
                addr.subnet = subnet


    def update_ipmi_interface(self, interface):
        if interface.address is None:
            self.log.info("Removing interface with no address: %s", interface)
            interface.host.interfaces.remove(interface)

        else:
            subnet = interface.address.query_subnet()

            for range in subnet.ranges:
                if range.range_type == 'dhcp' and range.contains(interface.address):
                    self.log.info("IPMI Port/Interface has dynamic address")
                    self.log.info("  %s", interface)
                    self.log.info("  %s", interface.address)

                    if not self.avail_ip_map.has_key(subnet):
                        self.avail_ip_map[subnet] = subnet.avail_ip_set()

                    ipvalue = self.avail_ip_map[subnet].pop()
                    interface.address = IpAddress(value=IpType.ntoa(ipvalue), subnet=subnet)
                    self.log.info("  New address: %s", interface.address)

