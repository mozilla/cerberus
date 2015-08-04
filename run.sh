#!/bin/bash

pushd . > /dev/null
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

rm -rf ./histograms Histograms.json &&
wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json -O Histograms.json &&
nodejs exporter/export.js &&
python alert/alert.py &&
python alert/post.py &&
python alert/expiring.py email

popd > /dev/null
