#!/usr/bin/python

import sys
import os
import threading
import time
import subprocess



class ReadThread(threading.Thread):
	THREADS = []

	@classmethod
	def joinall(cls):
		waiting = True
		while waiting:
			waiting = False
			for t in cls.THREADS:
				if t.isAlive():  t.join(0.1)
				waiting |= t.isAlive()

	def __init__(self, name, f):
		threading.Thread.__init__(self, name=name)
		self.daemon = True
		self.f = f

		self.THREADS.append(self)
		self.start()

	def run(self):
		line = self.f.readline()
		while line != "":
			self.handle(line[:-1])
			line = self.f.readline()

	def handle(self, line):
		print "%s: %s" % (self.name, line)

cmd = os.path.join(os.path.dirname(__file__), "makeoutput.py")
p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

t1 = ReadThread("STDOUT", p.stdout)
t2 = ReadThread("STDERR", p.stderr)
try:
	ReadThread.joinall()
	print "READTHREADS COMPLETE"
	rc = p.wait()
	print "PROCESS FINISHED: " , rc
except KeyboardInterrupt:
	print "Ctrl-C"
