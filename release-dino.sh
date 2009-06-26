#!/bin/sh

# This is run on the build server to add the current 
# ebuild to the OVERLAY 

OVERLAY_DIR=/mw/app/portage/OVERLAY
PORTAGE_GROUP=sys-cluster
SVN_URL="https://svn.metaweb.com/svn/se-packages/dino/dev/2.0"

if [ "$1" = "" ]; then
	echo "Must provide a version number"
	exit 1
fi

VERSION=$1
REVISION=$(svn log --limit 1 -q -r HEAD:1 ${SVN_URL} | awk '/^r/ {print $1}' | sed -e 's/r//')

echo "VERSION: ${VERSION}.${REVISION}"

SOURCE="${SVN_URL}/dino2-VERSION-r1.ebuild"
EBUILD="${OVERLAY_DIR}/${PORTAGE_GROUP}/dino2/dino2-${VERSION}.${REVISION}-r1.ebuild"

FILES=$(echo ${OVERLAY_DIR}/${PORTAGE_GROUP}/dino2/dino2-${VERSION}.*.ebuild)
if [[ -e $FILES ]]; then
	echo "Version already exists: ${FILES}"
	exit 1
fi


echo "DEST: ${EBUILD}"
rm -f ${EBUILD}
svn export ${SOURCE} ${EBUILD}
ebuild ${EBUILD} manifest
