#!/bin/bash

(cd exporter; npm install) &&
rm -rf ./histograms &&
wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json &&
nodejs exporter/export.js && python alert/alert.py
