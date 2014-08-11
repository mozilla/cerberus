#!/bin/bash

# To package the tarball:
# tar czvf cerberus-0.2.tar.gz *.sh alert/ dashboard/ exporter/ .git

sudo apt-get -qq update
sudo DEBIAN_FRONTEND=noninteractive apt-get -qq -y install nodejs npm python-numpy python-opencv python-matplotlib
if [ ! -d "output" ]; then
  mkdir -p output
fi

# Remember where we were
pushd .

REGRESSIONS=dashboard/regressions.json

# Fetch the previous alert file from S3
wget -O regressions_prev.json https://s3-us-west-2.amazonaws.com/telemetry-public-analysis/cerberus/data/regressions.json
if [ -s regressions_prev.json ]; then
    echo "regressions.json on S3 was not empty"
    cp regressions_prev.json $REGRESSIONS
else
    echo "regressions.json on S3 was empty"
fi

# Now run the update.
./run.sh

# Go back!
popd

# Copy updated file to output dir
cp $REGRESSIONS output/
