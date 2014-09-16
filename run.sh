#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

git pull
(cd exporter; npm install) &&
rm -rf ./histograms &&
wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json &&
nodejs exporter/export.js &&
python alert/alert.py &&
python alert/post.py

cd -
