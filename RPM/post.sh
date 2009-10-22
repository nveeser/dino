pylibdir=$(/mw/dino/bin/python -c 'import distutils.sysconfig as s; print s.get_python_lib()')
chmod -R 755 /${pylibdir}/dino/probe/probe-exec/*
chmod 755 /${pylibdir}/dino/generators/activate_dns.sh