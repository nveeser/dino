import sys
import os
from os.path import join, abspath, dirname, exists
import shutil
from nose.tools import *

from deploy import *



class TestDeploy(object):
	DATA_ROOT = abspath(join(dirname(__file__), "data"))

	@classmethod
	def get_datafile(cls, shortname):
	    path = os.path.join(cls.DATA_ROOT, shortname)
	    assert os.path.exists(path), "Could not find file: %s" % path
	    return path

	def test_deploy_parse(self):
		fp = self.get_datafile("map1")
		df = DeployFile(fp)

		eq_(len(df), 3)
		assert_true(isinstance(df[0], CopyEntry))
		assert_true(isinstance(df[1], TouchEntry))
		assert_true(isinstance(df[2], SymlinkEntry))


class TestCopy(TestDeploy):
	WORK_ROOT = abspath(join(dirname(__file__), "tempdata"))

	@classmethod
	def setUpClass(cls):
		if exists(cls.WORK_ROOT):
			shutil.rmtree(cls.WORK_ROOT)
		cls.indir = join(cls.WORK_ROOT, "in")
		os.makedirs(cls.indir)
		cls.outdir = join(cls.WORK_ROOT, "out")
		os.makedirs(cls.outdir)


	@classmethod
	def tearDown(cls):
		if exists(cls.WORK_ROOT):
			shutil.rmtree(cls.WORK_ROOT)


	def test_generator(self):

		def entry_test(source_files, deploy_lines, target_files):
			# Create Source Files
			#
			for f in source_files:
				path = join(self.indir, f)
				if path[-1] == '/':
					#print "dir: " + path
					os.makedirs(path)
				else:
					#print "file: " + path
					if not exists(dirname(path)):
						os.makedirs(dirname(path))
					shutil.copy("/bin/ls", path)

			# Execute Deploy Entries
			#
			df = DeployFile(defroot="/mw")
			for line in deploy_lines:
				df.parse_line(line)
			df.deploy(self.indir, self.outdir)

			# Validate Target Files
			#
			for t in target_files:
				path = join(self.outdir, t)
				if path[-1] == '/':
					assert_true(os.path.isdir(path), "Not Found: %s" % path)
				else:
					assert_true(os.path.isfile(path), "Not Found: %s" % path)


		args = (
			[ ("file",), ("file .",), ("mw/", "mw/file",) ],
			[ ("file",), ("file name",), ("mw/", "mw/name",) ],
			[ ("file",), ("file dir/",), ("mw/", "mw/dir/", "mw/dir/file",) ],
			[ ("dir/",), ("dir .",), ("mw/",) ],
			[ ("dir/",), ("dir dir",), ("mw/", "mw/dir/",) ],
			[ ("dir/x/file", "dir/x/file2"), ("dir .",), ("mw/", "mw/x/", "mw/x/file", "mw/x/file2") ],
			[ ("dir/x/file", "dir/x/file2"), ("dir dir",), ("mw/", "mw/dir/", "mw/dir/x/", "mw/dir/x/file", "mw/dir/x/file2") ],
		)
		for (source_files, deploy_lines, target_files) in args:
			yield entry_test, source_files, deploy_lines, target_files















