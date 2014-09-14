import simplejson as json
import poster

detector = poster.Detector("Histogram Regression Detector", "Histogram Regression Detector")
poster.set_server_url("http://localhost:8080")

# Update histogram definitions on the server and update subscriptions
with open('Histograms.json') as f:
    histograms = json.load(f)
    for name, description in histograms.iteritems():
        metric = poster.Metric(name, description['description'], detector)
        metric.realize()

# Post detected alerts
with open('dashboard/regressions.json') as f:
    regressions = json.load(f)
    poster.set_server_url("http://localhost:8080")
    detector = poster.Detector("Histogram Regression Detector", "Histogram Regression Detector")

    for date, regressions in regressions.iteritems():
        for histogram_name, regression in regressions.iteritems():
            metric = poster.Metric(histogram_name, regression['description'], detector)
            payload = {'reference_series': regression['reference'],
                       'series': regression['regression'],
                       'buckets': regression['buckets'],
                       'series_label': date,
                       'reference_series_label': 'Previous build-id',
                       'x_label': regression['description'],
                       'y_label': "Normalized Frequency Count",
                       'title': histogram_name,
                       'link': "telemetry.mozilla.org/#filter=nightly%2F" + histogram_name,
                       'type': 'graph'}
            poster.post_alert(detector, metric, payload, ",".join(regression['alert_emails']), date)
