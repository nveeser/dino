#!/bin/bash

### script: include
### ---------------
### Common functions for dino-probe components.
### Meant to be sourced from probe scripts. 
### 

### Set my real user name. 
###  
[[ `id -u` != "0" ]] && SUDO=sudo

### global vars
declare -x MW_ROOT=/usr/share/mw
declare -x P_CONF=$MW_ROOT/conf/dino-probe 
declare -x P_EXEC=$MW_ROOT/libexec/dino-probe
declare -x CLI=$MW_ROOT/libexec/dino-cli
declare -x CACHE=$MW_ROOT/var/probe-cache
### for python libs
declare -x PYTHONPATH="$PYTHONPATH:$P_EXEC/probes/bin"

### yaml cachefile routines

# get key
get_key() 
{
  KEY=$1
  VAL=$( python -c "import yaml; print yaml.load(open('$CACHE')).get('$KEY', {})" )
  [[ "$VAL" != "" ]] && return $VAL
}

# put key
put_key()
{
  KEY=$1
  RET=$( )    
}

# remove key


# create cachefile


# remove cachefile


