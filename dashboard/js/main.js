lastNightly = null;

function loadRegressions() {
  $.getJSON("./regressions.json", null, parseRegressions);
}

function parseRegressions(data) {
  var dates = Object.keys(data).map(function(value, index) {
    return Date.parse(value);
  }).sort().reverse();

  dates = dates.map(function(value, index) {
    return getFormattedDate(new Date(value));
  });

  displayRegressions(dates, data);
}

function getFormattedDate(dt) {
  return dt.toISOString().substring(0, 10);
}

function displayRegressions(dates, data) {
  dates.forEach(function(value) {
    displayRegressionsForDate(value, data[value]);
  });

  if (location.hash) {
    location.href = location.hash;
  }
}

function displayRegressionsForDate(date, regressions) {
  displayDateHeader(date);
  Object.keys(regressions).forEach(function(value) {
    displayRegression(date, value, regressions[value])
  });
  $('#loading').remove()
}

function displayDateHeader(date) {
  $('#regressions').append('<div id="' + date + '"class="row">' +
                             '<div class="col-md-12">' +
                               '<h3 class="text-center" style="background:#FAFAFA; padding:20px"> ' +
                                  'Distribution changes detected for build-id ' + date +
                                '</h3>' +
                              '</div>' +
                            '</div>');
  $('#date-selector').append('<li><a href="#' + date + '">' + date + '</a></li');
}

function displayRegression(date, histogramName, regression) {
  data = convertData(date, regression["buckets"], regression["regression"], regression["reference"]);
  data = google.visualization.arrayToDataTable(data);

  $('#regressions').append('<div class="row" + id="' + date + histogramName + '">' +
                             '<div class="col-md-12 title" id="graph-">' +
                                '<a href="http://telemetry.mozilla.org/#filter=nightly%2F' +
                                  lastNightly + '%2F' + histogramName + '">' +
                                  '<h5 class="text-center">' + histogramName + '</h5>' +
                                '</a>' +
                              '</div>' +
                            '</div>');

  var container = $('#regressions').append('<div class="row"><div class="col-md-12 graph" id="graph-"></div></div>');
  container = $('.graph', container);

  new google.visualization.LineChart(container.last()[0]).
    draw(data, {curveType: 'function',
                height: 500,
                colors: ['red', 'black'],
                chartArea: {top: 10, height: '80%'},
                vAxis: {
                  title: 'Normalized Frequency Count'
                },
                hAxis: {
                  title: regression['description'],
                  slantedText: true,
                  slatendTextAngle: 90,
                }
  });
}

function convertData(date, buckets, regression, reference) {
  var dt = new Date(Date.parse(date));
  dt.setDate(dt.getDate() - 1);
  dt = dt.toISOString().substring(0, 10);
  var result = [['Bucket', date, dt]]

  for (var i = 0; i < buckets.length; i++) {
    result.push([buckets[i].toString(), regression[i], reference[i]]);
  }

  return result;
}

function initTelemetry() {
  Telemetry.init(function() {
    var versions = Telemetry.versions();

    versions = versions.filter(function(v) {
      return /^nightly/.test(v);
    }).sort();

    lastNightly = versions[versions.length -1].split('/').pop();
    loadRegressions(lastNightly);
  });
}

google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(initTelemetry);
