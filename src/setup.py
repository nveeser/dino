import os, sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(name='dino',
    version='3.0',
    author='nicholas veeser',
    author_email='nicholas@metaweb.com',
    description='python tools for managing host inventory and configuration',
    packages=find_packages(exclude=["dino.test", "probe-exec/*"]),
    package_data={
        'dino' : [ "dino.cfg" ],
        'dino.db' : [ "migrate/*" ],
        'dino.probe' : [ "probe-exec/*", "probe-spec/*" ],
        'dino.generators' : [ "activate_dns.sh", "dns_merge.pl" ],
     }
    )
