from optparse import Option

from dino.cmd.command import with_session, DinoCommand
from dino.cmd.exception import *
from dino.cmd.edit import ElementFormCommand
from dino.db import *

class EditHostCommand(ElementFormCommand):
    NAME = "edithost"
    USAGE = "{ Host/<InstanceName> [ -o ] | -i } [ -f <filename> ]"
    GROUP = "data"
    OPTIONS = (
        Option('-o', dest='out', action='store_true', default=False),
        Option('-i', dest='input', action='store_true', default=False),
        Option('-f', dest='file', default=None),
        )

    def validate(self):
        if len(self.args) < 1 and not self.option.input:
            raise CommandArgumentError(self, "Must specify one ElementName")


    def create_form(self, session, processor):
        processor.show_type_info = False
        processor.show_headers = False

        host = self._find_element(session, assert_class='Host')

        instances = self.instance_generator(host.device)

        return processor.to_form(instances)

    def process_form(self, session, processor, form):
        desc = processor.update_all(form)

        for change in desc:
            self.log.info(str(change))
        if session.last_changeset:
            self.log.info("Submitted: %s", session.last_changeset)
        else:
            self.log.info("No Change: Not Submitted")

    def instance_generator(self, device):
        assert device is not None
        yield device

        assert device.host is not None
        yield device.host

        for port in device.ports:
            yield port
            if port.interface is not None:
                yield port.interface


class CreateHostCommand(ElementFormCommand):
    NAME = "createhost"
    USAGE = "{ Device/<InstanceName> [ -o ] | -i } [ -f <filename> ]"
    GROUP = "data"
    OPTIONS = (
        Option('-o', dest='out', action='store_true', default=False),
        Option('-i', dest='input', action='store_true', default=False),
        Option('-f', dest='file', default=None),
        )

    def validate(self):
        if len(self.args) < 1 and not self.option.input:
            raise CommandArgumentError(self, "Must specify one ElementName")


    def create_form(self, session, processor):
        processor.show_type_info = False
        processor.show_headers = False

        device = self._find_element(session, assert_class='Device')

        if not device:
            raise CommandArgumentError(self, "Device does not exist")
        if device.host is not None:
            raise CommandArgumentError(self, "Device already contains a Host")

        device.host = session.resolve_entity('Host').create_empty()
        Interface = session.resolve_entity('Interface')
        for port in device.ports:
            device.port.interface = Interface.create_empty()

        return processor.to_form(self.instance_generator())

    def process_form(self, session, processor, form):
        desc = processor.create_all(form)
        for change in desc:
            self.log.info(str(change))
        self.log.info("Submitted: %s", session.last_changeset)

    def instance_generator(self, device):
        assert device is not None
        yield device

        assert device.host is not None
        yield device.host

        for port in device.ports:
            yield port
            if port.interface is not None:
                yield port.interface



class DumpHostCommand(EditHostCommand):
    NAME = "dumphost"
    USAGE = "Host/<InstanceName> [ -f <filename> ]"
    GROUP = "data"
    OPTIONS = (
        Option('-f', dest='file', default=None),
    )

    def validate(self):
        if len(self.args) < 1:
            raise CommandArgumentError(self, "Must specify one Host ElementName")

    @with_session
    def execute(self, session):
        processor = ElementFormProcessor.create(session)

        form = self.create_form(session, processor)
        self.write_form(form)





