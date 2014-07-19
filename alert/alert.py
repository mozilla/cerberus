# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Search for regression in a histogram dump directory produced by the
# node exporter.

import json
import numpy
import cv2
import sys
import os
import matplotlib.pyplot as plt
import logging
import json
import pylab

from time import mktime, strptime
from datetime import datetime, timedelta

def add_to_series(series, measure):
    conv = strptime(measure['date'][:10], "%Y-%m-%d")
    series_it = series

    for idx, filter in enumerate(measure['filter'][:3]):
        if not filter in series_it:
            series_it[filter] = {}
        series_it = series_it[filter]

    dt = datetime.fromtimestamp(mktime(conv))

    if dt in series_it:
        series_it[dt] += numpy.array(measure["values"])
    else:
        series_it[dt] = numpy.array(measure["values"])

def compare_histograms(s, regressions, histogram, path="", nr_ref_days=7):
    if type(s) is dict:
        for filter in s:
            if type(filter) == datetime:
                compare_histogram(s, regressions, histogram, path, nr_ref_days)
                break
            else:
                compare_histograms(s[filter], regressions, histogram, path + "/" + filter)


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

def compare_histogram(s, regressions, histogram, path, nr_ref_days):
    # We want to check that the histogram of the current day and the ones of the
    # next "nr_future_days" days regress against the histograms of the past "nr_ref_days" days
    s = sorted(s.items(), key=lambda x: x[0])
    nr_future_days = 2

    for i, entry in enumerate(s[:-nr_future_days if nr_future_days else None]):
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
            regressions.append((dt, histogram, get_raw_histograms(comparisons)))

def process_file(filename, regressions):
    logging.debug("Processing " + filename)
    series = {}

    with open(filename) as f:
        measures = json.load(f)
        for measure in measures:
            filters = measure['filter']

            if filters[2] != "WINNT" or filters[1] != "Firefox" or filters[0] != "saved_session":
                continue

            add_to_series(series, measure)

        compare_histograms(series, regressions, os.path.basename(filename)[:-5])

def plot(histogram_name, raw_histograms):
    hist, ref_hist = raw_histograms
    pylab.plot(hist, label="Regression", color="red")
    pylab.plot(ref_hist, label="Reference", color="blue")
    pylab.legend(shadow=True)
    pylab.title(histogram_name)
    pylab.savefig('plot.png', bbox_inches='tight')

if __name__ == "__main__":
    regressions = []

    #logging.basicConfig(level=logging.DEBUG)
    #process_file('./histograms/FX_TAB_ANIM_ANY_FRAME_INTERVAL_MS.json', regressions)

    # Process all histograms
    for subdir, dirs, files in os.walk('./histograms'):
        for file in files:
            if file.endswith(".json"):
                process_file(subdir + "/" + file, regressions)

    # Load past regressions
    past_regressions = {}
    try:
        with open('regressions.json') as f:
            past_regressions = json.load(f)
    except:
        pass

    # Print new regressions
    for regression in sorted(regressions, key=lambda x: x[0]):
        dt, histogram, raw_histograms = regression
        dt = dt.strftime("%d/%m/%Y")

        if dt in past_regressions and histogram in past_regressions[dt]:
            print 'Regression found for '+ histogram + ", " + dt
        else:
            print 'Regression found for '+ histogram + ", " + dt + " [new]"

            plot(histogram, raw_histograms)

            if not dt in past_regressions:
                past_regressions[dt] = {}

            past_regressions[dt][histogram] = ""

            # Send regression alert

    # Store regressions found
    with open('regressions.json', 'w') as f:
        json.dump(past_regressions ,f)
