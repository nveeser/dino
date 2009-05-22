
from dino import LogObject

from subprocess import Popen


try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    #print("running with cElementTree on Python 2.5+")
except ImportError:
  try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      #print("running with ElementTree on Python 2.5+")
  except ImportError:
    try:
      from lxml import etree
      #print("running with lxml.etree")
    except ImportError:
          print("Failed to import ElementTree from any known place")


class Probe(LogObject):
    def run(self):
        pass
    
    def exec_process(self, cmd):
        pass
    