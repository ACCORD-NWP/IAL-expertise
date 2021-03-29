#!/bin/bash

# Script de deploiement du projet "davai" sur les calculateurs

# Parse args
if [ "$1" == "-h" ]; then
    echo "Usage: deploy.sh [VERSION]"
    echo "<VERSION> being the distant label, e.g. 'dev'"
    echo "If no VERSION is provided, the numbered version found in davai_tbx/__init__.py is used."
	echo "The distant installation is labelled davai-<VERSION>"
    exit
fi
VERSION=$1
if [ "$VERSION" == "" ]; then
    VERSION=`grep __version__ davai_tbx/__init__.py | awk '{print $3}' | awk -F "'" '{print $2}'`
fi
DAVAI_DIR="public/davai/$VERSION"


# Platforms to push onto
belenos=1
taranis=1
sxcoope1=1


# Filters
notests="--exclude tests"


# Rsync
logger="davai-$VERSION deployed on:\n"
echo "------------------------------------------------------"
if [ "$belenos" == 1 ]; then
  echo "...belenos..."
  rsync -avL * belenos:$DAVAI_DIR $notests
  logger="$logger - belenos\n"
fi
echo "------------------------------------------------------"
if [ "$taranis" == 1 ]; then
  echo "...taranis..."
  rsync -avL * taranis:$DAVAI_DIR $notests
  logger="$logger - taranis\n"
fi
echo "------------------------------------------------------"
if [ "$sxcoope1" == 1 ]; then
  echo "...sxcoope1..."
  rsync -avL * sxcoope1:$DAVAI_DIR $notests
  logger="$logger - sxcoope1\n"
fi


# Log final
echo "------------------------------------------------------"
echo -e $logger

