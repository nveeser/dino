#!/bin/sh

OVERLAY=/u/nicholas/portage
PORTAGE_GROUP=sys-cluster

if [ "$1" = "" ]; then
	echo "Must provide a version number"
	exit 1
fi

VERSION=$1
REVISION=$(svn log --limit 1 -q -r HEAD:1 | awk '/^r/ {print $1}' | sed -e 's/r//')


echo "VERSION: ${VERSION}.${REVISION}"

FILENAME="dino-VERSION-r1.ebuild"

EBUILD="${OVERLAY}/${PORTAGE_GROUP}/dino2/dino2-${VERSION}.${REVISION}-r1.ebuild"

mkdir -p `dirname ${EBUILD}`

rm -f ${EBUILD}

cp dino2-VERSION-r1.ebuild ${EBUILD}

echo "DEST: ${EBUILD}"
