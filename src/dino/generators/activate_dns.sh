#! /bin/bash

# check for root so that we dont have to do sudo everywhere here
#[ "$USER" != "root" ] &&  echo "$0 can only be run by root" && exit 2

# TODO: this needs to get the generated data file aka DNS_DATA_SOURCE_FILE

# find my blessed port
if [[ "$MW_BLESSED_PORT" == "" ]]; then
  echo "FATAL: Cannot find MW_BLESSED_PORT variable. Exiting."
  exit 1
else
  DNS_LISTEN=$(/sbin/ifconfig $MW_BLESSED_PORT | \
    grep 'inet addr:' | awk '{print $2}' | awk -F: '{print $2}')
fi

# setup vars
DNS_ROOT="/var/dns/internal"
CACHE_ROOT="/var/dns/cache"
DNS_DATA_FILE="$DNS_ROOT/root/data"
DNS_DATA_SOURCE_FILE="/mw/app/dino/dns/combined"

# grab a specific version of the internal data file.
# NOTE: this avoids race conditions with multiple activations.

# extract all ns records to 
# determine the list of domains
DOMAINS=$( cat $DNS_DATA_FILE | \
  grep -E '^\.' | \
  awk -F: '{print $1}' | \
  sed -e 's/^\.//g' | \
  sort -u )

# extract all networks to determine 
# network access files to touch
NETS=$( cat $DNS_DATA_FILE | \
  grep -vE '(127.0.0|^#|^[[:space:]]*$)' | \
  awk -F: '{print $2}' | \
  grep -E '^[[:digit:]]+' | \
  awk -F. '{print $1"."$2"."$3}' | \
  sort -u )

# create a file with the cache server ip 
# for each domain (forward and reverse).
for DOM in $DOMAINS; do
    [ ! -f $CACHE_ROOT/root/servers/$DOM ] && \
    echo "$DNS_LISTEN" > $CACHE_ROOT/root/servers/$DOM
done

# touch a file for each network so it
# can be served from the internal cache.
for N in $NETS; do
    [ ! -f $CACHE_ROOT/root/ip/$N ] && touch $CACHE_ROOT/root/ip/$N
done

# copy the generated config to the destination like /var/dns/internal/root/data
echo "Copying generated config $DNS_DATA_SOURCE_FILE to $DNS_DATA_FILE"
cp -f $DNS_DATA_SOURCE_FILE $DNS_DATA_FILE || exit 1
cd $DNS_ROOT

# update the data.cdb file by running tinydns-data
echo "Updating tinydns data file"
cd $DNS_ROOT/root
tinydns-data || exit 1

# restart services
echo "Restarting services"
svc -du /service/internal || exit 1
svc -du /service/cache || exit 1
svstat /service/internal  || exit 1
svstat /service/cache  || exit 1

exit 0
