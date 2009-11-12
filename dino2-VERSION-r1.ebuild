# Copyright 1999-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils
inherit subversion

REVISION=${PV##*.}
if [[ ${REVISION} == "99999" ]]; then 
	REVISION=HEAD
fi

ESVN_REPO_URI="https://svn.metaweb.com/svn/se-packages/dino/dev/3.0"
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
	
	"


src_compile() {
    pushd src
    distutils_src_compile
    popd
}


src_install() {
    pushd src
    distutils_src_install
    popd

    chmod -R 755 ${D}/${pylibdir}/dino/probe/probe-exec/*
    chmod 755 ${D}/${pylibdir}/dino/generators/activate_dns.sh

    mkdir -p ${D}/usr/bin
    mkdir -p ${D}/var/cache/dino
    cp ${WORKDIR}/dino2-${PV}/bin/wrapper.py ${D}/usr/bin/dinoadm
    cp ${WORKDIR}/dino2-${PV}/bin/wrapper.py ${D}/usr/bin/dino
    cp ${WORKDIR}/dino2-${PV}/bin/wrapper.py ${D}/usr/bin/dino-probe
    cp ${WORKDIR}/dino2-${PV}/bin/dino-discover ${D}/usr/bin/dino-discover

}
