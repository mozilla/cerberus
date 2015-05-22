# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Search for regression in a histogram dump directory produced by the
# node exporter.

import json
import urllib2
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from mail import send_ses
from version_compare import version_compare

HISTOGRAMS_FILE = "Histograms.json"
EMAIL_TIME_BEFORE = timedelta(weeks=1)
FROM_ADDR = "cerberus-alert@mozilla.com"

def get_future_release_dates():
    # scrape for future release date tables
    response = json.loads(urllib2.urlopen("https://wiki.mozilla.org/api.php?action=parse&format=json&page=RapidRelease/Calendar").read())
    soup = BeautifulSoup(response["parse"]["text"]["*"])
    table = soup.find(id="Future_branch_dates").find_parent("h2").find_next_sibling("table")
    result = {}
    for i, row in enumerate(table.find_all("tr")):
        if i == 0: continue # skip the header row
        version = list(row.find_all("td"))[-1].string.strip().replace("Firefox ", "")
        version = version.split(".")[0] # only keep the major version
        date_string = list(row.find_all("th"))[-1].string.strip(" \t\r\n*")
        try: result[version] = datetime.strptime(date_string, "%Y-%m-%d")
        except ValueError: pass
    return result

def is_expiring(histogram_entry, now, release_dates):
    # check if the expiration version is unknown, invalid, or far into the future
    expiry = histogram_entry.get("expires_in_version", "never").strip()
    if expiry in {"never", "default"}: return False
    try:
        max_release = next(release_dates.iterkeys())
        for release in release_dates.iterkeys():
            if version_compare(max_release, release) < 0:
                max_release = release
        if version_compare(expiry, max_release) > 0: return False
    except: # malformed version, assume that means it is expired
        return True

    # otherwise, it is probably a past version, so it is definitely expired
    if expiry not in release_dates: return True
    
    # known version, check if it is close to release
    return release_dates[expiry] - now < EMAIL_TIME_BEFORE

def main():
    with open(HISTOGRAMS_FILE) as f: histograms = json.load(f)
    now, release_dates = datetime.now(), get_future_release_dates()
    notifiable_histograms = sorted([h for h in histograms.items() if is_expiring(h[1], now, release_dates)], key=lambda h: h[0])
    
    # organize histograms into buckets indexed by email
    email_histogram_names = {}
    for name, entry in notifiable_histograms:
        if entry.get("alert_emails", False):
            for email in entry["alert_emails"]:
                if email not in email_histogram_names: email_histogram_names[email] = []
                email_histogram_names[email].append(name)
    
    # send out emails detailing the histograms that they are subscribed to that are expiring
    for email, expiring_histogram_names in email_histogram_names.items():
        email_body = """\
The following histograms will be expired on or before {}, and should be removed from the codebase:

{}

This is an automated message sent by Cerberus. See https://github.com/mozilla/cerberus for details and source code.
        """.format(
            (now + EMAIL_TIME_BEFORE).date(),
            "\n".join("* {}{} expires in version {}".format(
                "[SUBSCRIBED] " if name in expiring_histogram_names else "",
                name, entry["expires_in_version"])
                for name, entry in notifiable_histograms)
        )
        print("Sending email to {} with body:\n\n{}\n\n".format(email, email_body))
        send_ses(FROM_ADDR, "Telemetry Histogram Expiry", email_body, email)

if __name__ == "__main__":
    main()
