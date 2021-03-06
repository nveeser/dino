# Copyright 1999-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils
inherit subversion

#REVISION=${PV##*.}
REVISION=HEAD

ESVN_REPO_URI="https://svn.metaweb.com/svn/SANDBOX/nicholas/dino2"
ESVN_OPTIONS="-r $REVISION"

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
	
	>=dev-python/sqlalchemy-0.5.3
	dev-python/elixir	
	dev-python/mysql-python
	dev-python/lxml
	dev-python/pyyaml
	dev-python/simplejson

	"


src_install() {
	distutils_src_install

	mkdir -p ${D}/usr/bin
	cp ${WORKDIR}/dino2-${PV}/src/wrapper.py ${D}/usr/bin/dinoadm
	cp ${WORKDIR}/dino2-${PV}/src/wrapper.py ${D}/usr/bin/betty
	cp ${WORKDIR}/dino2-${PV}/dino-discover ${D}/usr/bin/dino-discover
}
