import os,sys

from subprocess import Popen, PIPE

if __name__ == "__main__":
    sys.path[0] = os.path.join(os.path.dirname(__file__), "..", "..", "..")


from dino.probe.impl import Probe

class IpmiProbe(Probe):
    pass
    