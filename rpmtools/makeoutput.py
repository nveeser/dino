#!/usr/bin/python

import sys
import threading
import time
import random

class DumpThread(threading.Thread):
	THREADS = []

	@classmethod
	def joinall(cls):
		try:
			waiting = True
			while waiting:
				waiting = False
				for t in cls.THREADS:
					if t.isAlive():  t.join(0.1)
					waiting |= t.isAlive()
		except KeyboardInterrupt:
			pass

	def __init__(self, name, fd, max=1000, wait_resolution=200):
		threading.Thread.__init__(self, name=name)
		self.daemon = True
		self.fd = fd
		self.max = max
		self.wait_resolution = wait_resolution
		self.count = 1

		self.THREADS.append(self)
		self.start()

	def run(self):
		while self.count < self.max:
			self.fd.write("%s: %d\n" % (self.name, self.count))
			self.fd.flush()
			self.count += 1
			wait = random.randint(0, self.wait_resolution)
			time.sleep(0.001 * wait)


t = DumpThread("stdout", sys.stdout, max=1000, wait_resolution=2)
t = DumpThread("stderr", sys.stderr, max=890, wait_resolution=2)

DumpThread.joinall()

