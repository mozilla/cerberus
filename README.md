cerberus
========

Automatic [alert system](http://mozilla.github.io/cerberus/dashboard/) for [telemetry](http://telemetry.mozilla.org/) histograms.

Cerberus detects changes in the distribution of histograms (histogram regressions), and posts alerts for these to the [medusa](https://github.com/mozilla/medusa) alert service.

Cerberus is also responsible for sending out email reminders for histograms that are expiring in upcoming versions.

The production instance is currently hosted on [telemetry-regression-alerts](ec2-52-13-120-199.us-west-2.compute.amazonaws.com) on the us-east-1 AWS region. All the production files live in `/mnt/telemetry/cerberus/`. There is a cronjob 

Code Overview
-------------

`run.sh` is a shell script that will set up all the dependencies, then do a full run of the Cerberus detectors. These are the components used in the script:

* `exporter/export.js` downloads the histogram evolutions from the [v4 aggregates API](https://github.com/vitillo/python_mozaggregator).
  * This script uses a custom fork of [telemetry-js-node](https://github.com/Uberi/telemetry-js-node/tree/v4-pipeline) that uses the v4 pipeline.
* The code for detecting regressions lives in `alert/alert.py`. This file is intended to be run as a script.
  * This is a script that reads histogram definitions from `Histograms.json` (which is downloaded automatically by `run.sh`).
  * Detected regressions are written out to `dashboard/regressions.json`.
* `alert/post.py` reads in new regressions from `dashboard/regressions.json`, and posts alerts to Medusa with this data.
  * Posting new alerts to Medusa is done using `alert/poster.py`.
  * By default, the Medusa server URL is set to `localhost:8080` - it expects to be on the same machine as the Medusa server. This can be changed by editing `alert/post.py`.
* `alert/expiring.py` is the histogram expiry detector - it notifies people via email when histograms are expiring soon.
  * Some configurable number of days before the versions where histograms are set to expire, it sends out emails using Amazon SES to watchers, and the dev-telemetry-alerts mailing list.
* `dashboard/` contains the telemetry regressions dashboard, which can be used to view regressions. It is intended to be hosted via GitHub Pages or a similar static hosting solution.

In production, there is a simple shell script, `/mnt/telemetry/update.sh`, that updates Cerberus and Medusa, triggered daily by a cronjob:

    #!/bin/bash
    cd /mnt/telemetry
    export PATH=$PATH:/usr/local/bin
    cd medusa; git pull
    cd ..
    cd cerberus; git pull
    ./run.sh &> ../cerberus.log
    cd ..
    iacomus-alerts/run.sh &> iacomus-alerts.log
    aws s3 cp medusa/resources/medusa.sqlite s3://telemetry-regressions-v1/medusa.sqlite &> s3backup.log

The crontab looks like this:

    5 4 * * * /mnt/telemetry/update.sh
