# Copyright 1999-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils
inherit subversion

REVISION=${PV##*.}
if [[ ${REVISION} == "99999" ]]; then 
	REVISION=HEAD
fi

ESVN_REPO_URI="https://svn.metaweb.com/svn/se-packages/dino/dev/2.5"
ESVN_OPTIONS="-r $REVISION"
ESVN_PROJECT="dino-trunk"

DESCRIPTION=""
HOMEPAGE=""

LICENSE=""
SLOT="0"
KEYWORDS="i386 amd64"
IUSE=""

DEPEND=">=dev-lang/python-2.4"
RDEPEND="
    >=dev-lang/python-2.4 
    sys-apps/pciutils
    sys-block/megacli
    sys-block/tw_cli
    net-dns/bind-tools

	sys-apps/lshw	
	
	dev-perl/Net-CDP
	net-libs/mw-libnet
	
	>=dev-python/sqlalchemy-0.5.3
	dev-python/elixir	
	dev-python/mysql-python
	dev-python/lxml
	dev-python/pyyaml
	dev-python/simplejson
	net-libs/libpcap
	
	"


src_install() {
	distutils_src_install
	
	pylibdir="$(${python} -c 'from distutils.sysconfig import get_python_lib; print get_python_lib()')"
    chmod -R 755 ${D}/$pylibdir/dino/probe/probe-exec/*
	chmod 755 ${D}/$pylibdir/dino/generators/activate_dns.sh
		
    pylibdir="$(${python} -c 'from distutils.sysconfig import get_python_lib; print get_python_lib()')"
    
    chmod -R 755 ${D}/$pylibdir/dino/probe/probe-exec/*
	chmod 755 ${D}/$pylibdir/dino/generators/activate_dns.sh
	
	
	mkdir -p ${D}/usr/bin
	mkdir -p ${D}/var/cache/dino
	cp ${WORKDIR}/dino2-${PV}/src/wrapper.py ${D}/usr/bin/dinoadm
	cp ${WORKDIR}/dino2-${PV}/src/wrapper.py ${D}/usr/bin/dino
	cp ${WORKDIR}/dino2-${PV}/src/wrapper.py ${D}/usr/bin/dino-probe
	cp ${WORKDIR}/dino2-${PV}/dino-discover ${D}/usr/bin/dino-discover
	
}
