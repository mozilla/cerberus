import simplejson as json
import poster

detector = poster.Detector("Histogram Regression Detector", "Histogram Regression Detector")
poster.set_server_url("http://localhost:8080")

# Load list of histogram names for which alerts should not be sent
try:
    with open("alert/ignored_histograms.json", "r") as f:
        ignored_histogram_names = set(json.load(f))
except IOError:
    ignored_histogram_names = set()

# Update histogram definitions on the server and update subscriptions
with open('Histograms.json') as f:
    histograms = json.load(f)

with open("Scalars.json") as f:
    scalars = json.load(f)

probes = dict(histograms.items() + scalars.items())

for name, description in probes.iteritems():
    metric = poster.Metric(name, description['description'], detector)
    metric.realize()

# Post detected alerts
with open('dashboard/regressions.json') as f:
    regressions = json.load(f)

    for date, regressions in regressions.iteritems():
        for histogram_name, regression in regressions.iteritems():
            if histogram_name not in ignored_histogram_names:
                metric = poster.Metric(histogram_name, regression['description'], detector)
                payload = {'reference_series': regression['reference'],
                           'series': regression['regression'],
                           'buckets': regression['buckets'],
                           'series_label': date,
                           'reference_series_label': 'Previous build-id',
                           'x_label': regression['description'],
                           'y_label': "Normalized Frequency Count",
                           'title': histogram_name,
                           'link': "http://telemetry.mozilla.org/new-pipeline/dist.html#!measure={histogram_name}&product=Firefox&start_date={date}&end_date={date}&table=0&use_submission_date=0".format(date=date, histogram_name=histogram_name),
                           'type': 'graph'}
                poster.post_alert(detector, metric, payload, ",".join(regression['alert_emails']), date)
