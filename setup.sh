#!/usr/bin/env bash

BASEDIR=$(dirname $0)
cd $BASEDIR
python3 -m venv venv
venv/bin/pip install websockets==10.0
venv/bin/pip install pygame==2.0.1
venv/bin/pip install pygame-gui==0.5.7

chmod u+x Client.py
echo 'Installation completed.'
