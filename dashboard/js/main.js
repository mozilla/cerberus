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
}

function displayRegressionsForDate(date, regressions) {
  displayDateHeader(date);
  Object.keys(regressions).forEach(function(value) {
    displayRegression(value, regressions[value])
  });
}

function displayDateHeader(date) {
  $('#regressions').append('<div class="row"><div class="col-md-12>"><h2 class="text-center">' + date + '</h2></div></div>');
}

var cnt = 0;

function displayRegression(histogramName, regression) {
  data = convertData(regression["buckets"], regression["regression"], regression["reference"]);
  data = google.visualization.arrayToDataTable(data);

  var container = $('#regressions').append('<div class="row"><div class="col-md-12" id="graph-"' + cnt + '></div></div>');
  container = $('.col-md-12', container);

  new google.visualization.LineChart(container.last()[0]).
    draw(data, {curveType: 'function',
                smoothLine: false,
                title: histogramName,
                height: 500,
                colors: ['red', 'black']});
}

function convertData(buckets, regression, reference) {
  var result = [['Bucket', 'Regression', 'Reference']]

  for (var i = 0; i < buckets.length; i++) {
    result.push([buckets[i].toString(), regression[i]*100, reference[i]*100]);
  }

  return result;
}

google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(loadRegressions);
