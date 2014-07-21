#!/bin/bash

(cd exporter; npm install) &&
rm -rf ./histograms &&
nodejs exporter/export.js && python alert/alert.py
