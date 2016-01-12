#!/bin/bash

# THIS SCRIPT STARTS TELEMETRY ALERTS PROCEDURES; IT SHOULD BE RUN DAILY

pushd . > /dev/null
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

rm -rf ./histograms Histograms.json &&
wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json -O Histograms.json && # update histogram metadata
nodejs exporter/export.js && # export histogram evolutions using Telemetry.js to JSON, under `histograms/*.JSON`
python alert/alert.py && # perform regression detection and output all found regressions to `dashboard/regressions.json`
python alert/post.py && # post all the found regressions above to Medusa, the Telemetry alert system
python alert/expiring.py email # detect expiring/expired histograms and alert the associated people via email

popd > /dev/null
