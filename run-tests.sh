#!/bin/bash

CURR=$(dirname $(readlink -f $0))

cd $CURR
source virtualenv/bin/activate
nosetests $@
