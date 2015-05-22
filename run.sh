#!/bin/bash

sudo apt-get -qq update
sudo DEBIAN_FRONTEND=noninteractive apt-get -qq -y install python-simplejson python-boto nodejs npm python-numpy python-opencv python-matplotlib

pushd .
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

git pull
(cd exporter; npm install) &&
rm -rf ./histograms &&

wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json -O Histograms.json &&
nodejs exporter/export.js &&
python alert/alert.py &&
python alert/post.py &&
python alert/expiring.py email

popd
