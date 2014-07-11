#!/bin/bash

cd exporter
npm install
cd ..

node exporter/export.js
python alert/alert.py 2>&1 | tee regressions
