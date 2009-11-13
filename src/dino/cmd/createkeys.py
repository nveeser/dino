from optparse import Option
import os
import tempfile

from dino.cmd.command import with_session, DinoCommand
from dino.command import *
from dino.db import *
import subprocess

class CreateKeys(DinoCommand):

    '''Create rsa and dsa keys for ssh access to a host.'''

    NAME = "createkeys"
    USAGE = "Host:<InstanceName>"
    GROUP = "data"
    OPTIONS = (
        Option('-f', dest='force', action='store_true', default=False),
        )

    def validate(self, opts, args):
        if len(args) != 1:
            raise CommandArgumentError(self, "Command must have one Host argument")


    def create_key(self, key_type='dsa'):
        if key_type not in ('dsa', 'rsa'):
            raise ValueError("Method must have dsa or rsa key_type. Invalid Type: %s" % key_type)

        self.log.info("Generate: %s" % key_type)

        temp = tempfile.NamedTemporaryFile()
        self.log.finer("  TempFile: %s" % temp.name)

        args = ["/usr/bin/ssh-keygen", '-q', '-C', 'Host Key', '-t', key_type, '-N', '', '-f', temp.name]
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (out, err) = p.communicate("y")
        if out:
            for line in out.split("\n"):
                self.log.info("  OUTPUT: %s", line)
        if err:
            for line in err.split("\n"):
                self.log.error("  STDERR: %s", line)

        priv_key = temp.read()
        temp.close()

        f = open(temp.name + '.pub', 'r')
        pub_key = f.read()
        f.close()

        os.unlink("%s.pub" % temp.name)

        return (pub_key, priv_key)

    @with_session
    def execute(self, session, opts, args):
        instance_name = args[0]

        resolver = session.spec_parser.parse(args[0])

        host = resolver.resolve().next()
        if host is None:
            raise CommandArgumentError(self, "Cannot find Host: %s" % instance_name)

        session.open_changeset()

        rsa_pub, rsa_priv = self.create_key('rsa')
        dsa_pub, dsa_priv = self.create_key('dsa')

        if host.ssh_key_info is None:
            i = SshKeyInfo(rsa_key=rsa_priv, rsa_pub=rsa_pub, dsa_key=dsa_priv, dsa_pub=dsa_pub)
            host.ssh_key_info = i

        elif opts.force:
            host.ssh_key_info.set(rsa_key=rsa_priv, rsa_pub=rsa_pub, dsa_key=dsa_priv, dsa_pub=dsa_pub)

        else:
            self.log.error("Host has existing key information. Supply -f to override")
            return

        cs = session.submit_changeset()

        self.log.info("Submitted: %s", cs)

