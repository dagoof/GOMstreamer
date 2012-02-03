#!/bin/sh
####################
EMAIL='youremail@example.com'
PASSWORD='PASSWORD'
QUALITY='SQTest'
MODE='save'
DUMPFILE='dump.ogm'
DUMPDIR='saves'
####################
PARENT_DIR="$(dirname "$( cd "$( dirname "$0" )" && pwd )")"
python "$PARENT_DIR/gomstreamer.py" -e $EMAIL -p $PASSWORD -q $QUALITY -m $MODE -o $DUMPFILE -b $DUMPDIR $*
