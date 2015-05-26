# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Search for regression in a histogram dump directory produced by the
# node exporter.

import json
import os
import sys
import urllib2
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup
from mail import send_ses
from mozilla_versions import version_compare, version_get_major, version_normalize_nightly

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

NOTIFICATIONS_FILE = os.path.join(SCRIPT_DIR, "already_notified_histograms.json")
HISTOGRAMS_FILE = os.path.join(SCRIPT_DIR, "Histograms.json")
EMAIL_TIME_BEFORE = timedelta(weeks=1)
FROM_ADDR = "telemetry-alert@mozilla.com"

def get_future_release_dates():
    """Obtain a dictionary mapping future Firefox version numbers to their intended release date.

Takes data from the RapidRelease page of the Mozilla Wiki. The page is expected to be in the following form:

    (...beginning of document...)
    <h2><span id="Future_branch_dates">(TITLE)</span></h2>
    (...anything other than a table...)
    <table>
      (header row)
      <tr>
        (..other columns...)
        <th>(expected merge date as YYYY-MM-DD)</th>
        <td>Firefox (Firefox nightly)</td>
        <td>Firefox (Firefox aurora)</td>
        <td>Firefox (Firefox beta)</td>
        <th>(expected release date as YYYY-MM-DD)</th>
        <td>Firefox (Firefox release)</td>
      </tr>
      (...other rows...)
    </table>
    (...rest of document...)"""
    # scrape for future release date tables
    response = json.loads(urllib2.urlopen("https://wiki.mozilla.org/api.php?action=parse&format=json&page=RapidRelease/Calendar").read())
    soup = BeautifulSoup(response["parse"]["text"]["*"])
    table = soup.find(id="Future_branch_dates").find_parent("h2").find_next_sibling("table")
    result = {}
    for i, row in enumerate(table.find_all("tr")):
        if i < 2: continue # skip the header row and the current release version
        fields = list(row.find_all("td"))
        nightly_version = str(version_get_major(fields[-4].string.replace("Firefox ", ""))) + ".0a1"
        aurora_version  = str(version_get_major(fields[-3].string.replace("Firefox ", ""))) + ".0a2"
        beta_version    = str(version_get_major(fields[-2].string.replace("Firefox ", ""))) + ".0b1"
        release_version = str(version_get_major(fields[-1].string.replace("Firefox ", ""))) + ".0"
        
        release_date_string = list(row.find_all("th"))[-1].string.strip(" \t\r\n*")
        try:
            release_date = datetime.strptime(release_date_string, "%Y-%m-%d").date()
            result[aurora_version] = release_date
            result[beta_version] = release_date
            result[release_version] = release_date
        except ValueError: pass
        
        nightly_date_string = list(row.find_all("th"))[0].string.strip(" \t\r\n*")
        try:
            nightly_date = datetime.strptime(nightly_date_string, "%Y-%m-%d").date()
            result[nightly_version] = nightly_date
        except ValueError: pass
    return result

def is_expiring(histogram_entry, now, release_dates):
    # check if the histogram expires or not
    expiry_version = histogram_entry.get("expires_in_version", "never").strip()
    if expiry_version in {"never", "default"}: return False

    # check if the expiration version has a known release date
    expiry_version = version_normalize_nightly(expiry_version)
    if expiry_version in release_dates:
        return release_dates[expiry_version] == now + EMAIL_TIME_BEFORE
    return False # version expires in an unknown future version

def email_histogram_subscribers(now, notifiable_histograms):
    # organize histograms into buckets indexed by email
    email_histogram_names = {}
    for name, entry in notifiable_histograms:
        if name not in already_notified_histograms:
            for email in entry.get("alert_emails", []):
                if email not in email_histogram_names: email_histogram_names[email] = []
                email_histogram_names[email].append(name)

    # send emails to users detailing the histograms that they are subscribed to that are expiring
    for email, expiring_histogram_names in email_histogram_names.items():
        email_body = """\
The following histograms will be expired on or before {}, and should be removed from the codebase:

{}

This is an automated message sent by Cerberus. See https://github.com/mozilla/cerberus for details and source code.
        """.format(
            (now + EMAIL_TIME_BEFORE).date(),
            "\n".join("* {} expires in version {}{}".format(
                name, entry["expires_in_version"],
                " [SUBSCRIBED]" if name in expiring_histogram_names else "")
                for name, entry in notifiable_histograms)
        )
        print("Sending email to {} with body:\n\n{}\n\n".format(email, email_body))
        send_ses(FROM_ADDR, "Telemetry Histogram Expiry", email_body, email)

def get_expiring_histograms(now, release_dates, histograms):
    return sorted([
        (name, entry) for name, entry in histograms.items() if is_expiring(entry, now, release_dates)
    ], key=lambda h: h[0])

def run_tests():
    release_dates1 = {
      "38.0a1": datetime(2015, 6, 2),
      "39.0a1": datetime(2015, 6, 30),
      "40.0a1": datetime(2015, 8, 11),
      "41.0a1": datetime(2015, 9, 22),
      "42.0a1": datetime(2015, 11, 3),
      "43.0a1": datetime(2015, 12, 15),
      "44.0a1": datetime(2016, 1, 26),
      "45.0a1": datetime(2016, 3, 8),
      "46.0a1": datetime(2016, 4, 19),
      "47.0a1": datetime(2016, 5, 31),
    }
    release_dates2 = {
      "41.0a1": datetime(2015, 9, 22),
      "42.0a1": datetime(2015, 11, 3),
      "43.0a1": datetime(2015, 12, 15),
    }
    histograms = {
        "a": {"expires_in_version": "40"},
        "b": {"expires_in_version": "40"},
        "c": {"expires_in_version": "40.5"},
        "d": {"expires_in_version": "50"},
        "e": {"expires_in_version": "50"},
        "f": {"expires_in_version": "42"},
        "g": {"expires_in_version": "45"},
        "h": {"expires_in_version": "50a4"},
    }
    assert get_expiring_histograms(datetime(2015, 8, 3), release_dates1, histograms) == []
    assert get_expiring_histograms(datetime(2015, 8, 4), release_dates1, histograms) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"})]
    assert get_expiring_histograms(datetime(2015, 8, 5), release_dates1, histograms) == []
    assert get_expiring_histograms(datetime(2015, 9, 1), release_dates2, histograms) == []
    assert get_expiring_histograms(datetime(2015, 10, 26), release_dates2, histograms) == []
    assert get_expiring_histograms(datetime(2015, 10, 27), release_dates2, histograms) == [("f", {"expires_in_version": "42"})]
    assert get_expiring_histograms(datetime(2015, 10, 28), release_dates2, histograms) == []

    print "All tests passed!"
    sys.exit()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"list", "email", "test"}:
        print "Usage: {} list|email|test".format(sys.argv[0])
        print "  {} list    list histograms that are soon expiring".format(sys.argv[0])
        print "  {} email   notify users of histograms that are soon expiring".format(sys.argv[0])
        print "  {} test    run various internal tests".format(sys.argv[0])
        sys.exit(1)
    if sys.argv[1] == "test": run_tests()

    # get a list of histograms that are expiring and net yet notified about, sorted alphabetically
    with open(HISTOGRAMS_FILE) as f: histograms = json.load(f)
    now, release_dates = date.today(), get_future_release_dates()
    now = date.today()
    notifiable_histograms = get_expiring_histograms(now, release_dates, histograms)
    if sys.argv[1] == "list":
        for name, entry in notifiable_histograms:
            print("{} expires in version {}{}".format(
                name, entry["expires_in_version"],
                " (watched by {})".format(", ".join(email for email in entry["alert_emails"])) if "alert_emails" in entry else ""
            ))
    else: # send out emails
        email_histogram_subscribers(now, notifiable_histograms)

if __name__ == "__main__":
    main()