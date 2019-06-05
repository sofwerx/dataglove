#!/bin/bash
# PyBluez setup script
# James Andrews <Jandrews7348@floridapoly.edu>
sudo apt-get install python3
sudo apt-get install pkg-config libboost-python-dev libboost-thread-dev libbluetooth-dev libglib2.0-dev python-dev
#Configure gattlib for python3
pip3 download gattlib
tar xvzf ./gattlib-0.20150805.tar.gz
rm gattlib-0.20150805.tar.gz
chmod -Rv a+rwx gattlib-0.20150805/
cd gattlib-0.20150805/
sed -ie 's/boost_python-py34/boost_python-py37/' setup.py
pip3 install .
echo "done!"
