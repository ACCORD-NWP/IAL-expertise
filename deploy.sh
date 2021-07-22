#!/bin/bash

# Script de deploiement du projet "ial_expertise" sur les calculateurs

# Parse args
if [ "$1" == "-h" ]; then
    echo "Usage: deploy.sh [VERSION]"
    echo "<VERSION> being the distant label, e.g. 'dev'"
    echo "If no VERSION is provided, the numbered version found in ial_expertise/__init__.py is used."
	echo "The distant installation is labelled 'ial_expertise-<VERSION>'"
    exit
fi
VERSION=$1
if [ "$VERSION" == "" ]; then
    VERSION=`grep __version__ ial_expertise/__init__.py | awk '{print $3}' | awk -F "'" '{print $2}'`
fi
DEPLOY_DIR="public/ial_expertise/$VERSION"


# Platforms to push onto
platforms="belenos taranis sxcoope1"
belenos=1
taranis=1
sxcoope1=1


# Filters
notests="--exclude tests"


# Rsync
logger="'ial_expertise-$VERSION' deployed on:\n"
echo "------------------------------------------------------"
for platform in $platforms
  do
    echo "...${platform}..."
    #rsync -avL * $platform:$DEPLOY_DIR $notests
    logger="$logger - ${platform}\n"
  done

#echo "------------------------------------------------------"
#if [ "$belenos" == 1 ]; then
#  echo "...belenos..."
#  rsync -avL * belenos:$DEPLOY_DIR $notests
#  logger="$logger - belenos\n"
#fi
#echo "------------------------------------------------------"
#if [ "$taranis" == 1 ]; then
#  echo "...taranis..."
#  rsync -avL * taranis:$DEPLOY_DIR $notests
#  logger="$logger - taranis\n"
#fi
#echo "------------------------------------------------------"
#if [ "$sxcoope1" == 1 ]; then
#  echo "...sxcoope1..."
#  rsync -avL * sxcoope1:$DEPLOY_DIR $notests
#  logger="$logger - sxcoope1\n"
#fi


# Log final
echo "------------------------------------------------------"
echo -e $logger

