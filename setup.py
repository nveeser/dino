
from distutils.core import setup

import os,sys


def find_packages(src_dir):
    pkgs = []
    for root, dirs, files in os.walk(src_dir):
        src_len = len(src_dir)+1
        for file in files:
            if file.endswith("__init__.py"):                
                pkg_name = root[src_len:].replace("/",".")
                if pkg_name == "dino.test":
                    continue
                pkgs.append(pkg_name)
    return pkgs

            
setup(name='dino',
    version='2.5',
    author='nicholas veeser',
    author_email='nicholas@metaweb.com',
    description='python tools for managing host inventory and configuration',
    packages=find_packages("src"),
    package_dir = {'': 'src'},
    package_data = {
        'dino' : [ "dino.cfg" ], 
        'dino.db' : [ "migrate/*" ],
        'dino.probe' : [ "probe-exec/*", "probe-spec/*" ],
        'dino.generators' : [ "activate_dns.sh", "dns_merge.pl" ],
     }     
    )