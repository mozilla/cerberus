import simplejson as json
import urllib
import urllib2
import time

server = ""

def GET(uri, params):
    params = urllib.urlencode(params)
    req = urllib2.Request(server + uri + "?" + params , headers={'Accept': 'application/json'})
    return json.loads(urllib2.urlopen(req).read())

def POST(uri, params):
    params = json.dumps(params)
    req = urllib2.Request(server + uri, params, headers={'Content-Type': 'application/json',
                                                         'Accept': 'application/json'})
    response = json.loads(urllib2.urlopen(req).read())
    return response["id"]

def set_server_url(url):
    global server
    server = url

class Detector:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def get_id(self):
        try:
            return self.id
        except AttributeError:
            try:
                detectors = GET("/detectors/", {'name': self.name})
                self.id = detectors[0]['id']
            except urllib2.HTTPError as e:
                self.id = POST("/detectors/", {'name': self.name, 'url': self.url})

            return self.id

    def realize(self):
        self.get_id()

class Metric:
    def __init__(self, name, descr, detector):
        self.name = name
        self.descr = descr
        self.detector = detector

    def get_id(self):
        try:
            return self.id
        except AttributeError:
            uri = "/detectors/" + str(self.detector.get_id()) + "/metrics/"

            try:
                metrics = GET(uri, {'name': self.name})
                return metrics[0]['id']
            except urllib2.HTTPError as e:
                return POST(uri, {'name': self.name, 'description': self.descr})

    def realize(self):
        self.get_id()

def post_alert(detector, metric, payload, emails="", date=time.strftime("%Y-%m-%d")):
    try:
        payload = json.dumps(payload)
        uri = "/detectors/" + str(detector.get_id()) + "/metrics/" + str(metric.get_id()) + "/alerts/"
        return POST(uri, {'description': payload, 'date': date, 'emails': emails})
    except urllib2.HTTPError as e:
        if e.code == 422:
            print "Alert for detector: " + detector.name + ", metric: " + metric.name + ", has already been submitted!"
        else:
            raise e

if __name__ == "__main__":
    set_server_url("http://localhost:8080")
    detector = Detector("Histogram Regression Detector", "foobar")
    metric = Metric("metric100", "foobar", detector)
    post_alert(detector, metric, "foobar")
