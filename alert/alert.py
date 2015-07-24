# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Search for regression in a histogram dump directory produced by the
# node exporter.

import matplotlib.pyplot as plt

import json
import numpy
import cv2
import sys
import os
import logging
import json
import pylab
import os.path
import argparse

from time import mktime, strptime
from datetime import datetime, timedelta

histograms = None
args = None

PLOT_FILENAME = "plot.png"
REGRESSION_FILENAME = "dashboard/regressions.json"
HISTOGRAM_DB = "Histograms.json"

def has_not_enough_data(hist):
    return numpy.sum(hist) < 1000 or numpy.max(hist) < 1000

def normalize(hist):
    hist = hist.astype('float32')
    return hist / numpy.sum(hist)

def bat_distance(hist, ref):
    return cv2.compareHist(hist, ref, 3) # Bhattacharyya distance

def compare_range(series, idx, range, nr_ref_days):
    dt, hist = series[idx]
    hist = normalize(hist)
    dists = []
    logging.debug("Comparing " + dt.strftime("%d/%m/%Y"))

    for jdx in range:
        ref_dt, ref_hist = series[jdx]
        logging.debug("To " + ref_dt.strftime("%d/%m/%Y"))

        if has_not_enough_data(ref_hist):
            logging.debug("Reference histogram has not enough data")
            continue

        ref_hist = normalize(ref_hist)
        dists.append(bat_distance(hist, ref_hist))

    if len(dists):
        logging.debug('Bhattacharyya distance: ' + str(dists[-1]))
        logging.debug('Standard deviation of the distances: ' + str(numpy.std(dists)))

    if len(dists) > nr_ref_days/2 and dists[-1] > 0.12 and numpy.std(dists) <= 0.01:
        logging.debug("Suspicious difference found")
        return (hist, ref_hist)
    else:
        logging.debug("No suspicious difference found")
        return (None, None)

def get_raw_histograms(comparisons):
    hist = None
    ref_hist = None

    for h, r in comparisons:
        if h is not None:
            return (h, r)

    assert(False)

def compare_histogram(series, histogram, buckets, path, nr_ref_days = 7, nr_future_days = 2):
    """
Compare the past `nr_future_days` days worth of histograms in `series` to the past `nr_ref_days` days worth of histograms in `series` for regressions.

Returns a list of the detected regressions.
    """
    regressions = []
    series = sorted(series.items(), key=lambda x: x[0])

    for i, entry in enumerate(series[:-nr_future_days if nr_future_days else None]):
        dt, hist = entry

        logging.debug("======================")
        logging.debug("Analyzing " + dt.strftime(", %d/%m/%Y"))

        if has_not_enough_data(hist):
            logging.debug("Histogram has not enough data")
            continue

        comparisons = []
        ref_range = range(max(i - nr_ref_days, 0), i)

        for j in range(i, min(i + nr_future_days + 1, len(s))):
            comparisons.append(compare_range(s, j, ref_range, nr_ref_days))

        if len(comparisons) == sum(map(lambda x: x != (None, None), comparisons)):
            logging.debug('Regression found for '+ histogram + dt.strftime(", %d/%m/%Y"))
            regressions.append((dt, histogram, buckets, get_raw_histograms(comparisons)))
    return regressions

def process_file(filename, regressions):
    logging.debug("Processing " + filename)
    series = {}
    buckets = []

    regressions = []
    with open(filename) as f:
        measures = json.load(f)
        for measure in measures:
            # determine the date of the entry
            assert "date" in measure, "Missing date in measure"
            conv = strptime(measure['date'][:10], "%Y-%m-%d")
            measure_date = datetime.fromtimestamp(mktime(conv))
            
            # Get the values of the 
            assert measure_date not in series, "Duplicate entry for date {}".format(dt)
            series[measure_date] = numpy.array(measure["values"])
            buckets = measure['buckets']

        measure_name = os.path.splitext(os.path.basename(filename))[0] # Filename without extension
        regressions += compare_histogram(series, measure_name, buckets, "saved_session/Firefox/WINNT")
    return regressions

def plot(histogram_name, buckets, raw_histograms):
    hist, ref_hist = raw_histograms

    fig = pylab.figure(figsize=(len(buckets)/3, 10))
    pylab.plot(hist, label="Regression", color="red")
    pylab.plot(ref_hist, label="Reference", color="blue")
    pylab.legend(shadow=True)
    pylab.title(histogram_name)
    pylab.xlabel("Bin")
    pylab.ylabel("Normalized Weight")

    pylab.xticks(range(0, len(buckets)))
    locs, labels = pylab.xticks()
    pylab.xticks(locs, buckets, rotation="45")

    pylab.savefig(PLOT_FILENAME, bbox_inches='tight')
    pylab.close(fig)

def main():
    global histograms
    regressions = []

    with open("Histograms.json") as f:
        histograms = json.load(f)

    #logging.basicConfig(level=logging.DEBUG)
    #process_file('./histograms/FX_TAB_ANIM_ANY_FRAME_INTERVAL_MS.json', regressions)

    # Process all histograms
    for subdir, dirs, files in os.walk('./histograms'):
        for file in files:
            if file.endswith(".json"):
                regressions += process_file(subdir + "/" + file, regressions)

    # Load past regressions
    past_regressions = {}
    try:
        with open(REGRESSION_FILENAME) as f:
            past_regressions = json.load(f)
    except:
        pass

    # Print new regressions
    for regression in sorted(regressions, key=lambda x: x[0]):
        regression_date, histogram, buckets, raw_histograms = regression
        regression_timestamp = regression_date.isoformat()[:10]

        if regression_timestamp in past_regressions and histogram in past_regressions[regression_timestamp]:
            print 'Regression found for '+ histogram + ", " + regression_timestamp
        else:
            print 'Regression found for '+ histogram + ", " + regression_timestamp + " [new]"

            if not regression_timestamp in past_regressions:
                past_regressions[regression_timestamp] = {}

            descriptor = past_regressions[regression_timestamp][histogram] = {}
            descriptor["buckets"] = buckets
            descriptor["regression"] = raw_histograms[0].tolist()
            descriptor["reference"] = raw_histograms[1].tolist()

            name = histogram
            if histogram.startswith("STARTUP"):
                name = histogram[8:]
            descriptor["description"] = histograms.get(name, {}).get("description", "")
            descriptor["alert_emails"] = histograms.get(name, {}).get("alert_emails", "")

    # Store regressions found
    with open(REGRESSION_FILENAME, 'w') as f:
        json.dump(past_regressions ,f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telemetry Regression Detector",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    args = parser.parse_args()

    main()
