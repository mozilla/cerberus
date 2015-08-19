# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import sys
import urllib2
from datetime import datetime, date, timedelta

from bs4 import BeautifulSoup
from mail import send_ses
from mozilla_versions import version_compare, version_get_major, version_normalize_nightly

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

HISTOGRAMS_FILE         = os.path.join(SCRIPT_DIR, "..", "Histograms.json") # histogram definitions file
EMAIL_TIME_BEFORE       = timedelta(weeks=1) # release future date offset
FROM_ADDR               = "telemetry-alerts@mozilla.com" # email address to send alerts from
GENERAL_TELEMETRY_ALERT = "dev-telemetry-alerts@lists.mozilla.org" # email address that will receive all notifications

def get_version_table_dates(table):
    """Given a version table, obtains a dictionary mapping Firefox version numbers to their intended release date.

The table is expected to be in the following form:

    <table>
      (...other rows...)
      <tr>
        (..other td columns...)
        <th>(expected merge date as YYYY-MM-DD)</th>
        <td>Firefox (Firefox nightly)</td>
        <td>Firefox (Firefox aurora)</td>
        <td>Firefox (Firefox beta)</td>
        <th>(expected release date as YYYY-MM-DD)</th>
        <td>Firefox (Firefox release)</td>
      </tr>
      (...other rows...)
    </table>"""
    result = {}
    for row in table.find_all("tr"):
        # obtain the row and make sure it is valid (this skips the header row and any minor version rows)
        fields = list(row.find_all("td"))
        if len(fields) < 4: continue # not enough fields in the row, probably a header row
        is_valid = True
        for field in fields[-4:]: # ensure that each column represents a Firefox version
            if "Firefox" not in field.string:
                is_valid = False
                break
        if not is_valid: continue

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

def get_release_dates():
    """Obtain a dictionary mapping future Firefox version numbers to their intended release date.

Takes data from the RapidRelease page of the Mozilla Wiki. The page is expected to be in the following form:

    (...beginning of document...)
    <h2><span id="Future_branch_dates">(TITLE)</span></h2>
    (...anything other than a table...)
    (...version table...)
    (...more content...)
    <h2><span id="Past_branch_dates">(TITLE)</span></h2>
    (...anything other than a table...)
    (...version table...)
    (...rest of document...)"""
    response = json.loads(urllib2.urlopen("https://wiki.mozilla.org/api.php?action=parse&format=json&page=RapidRelease/Calendar").read())
    soup = BeautifulSoup(response["parse"]["text"]["*"])
    
    # scrape for future release date tables
    table = soup.find(id="Future_branch_dates").find_parent("h2").find_next_sibling("table")
    result = get_version_table_dates(table)
    
    # scrape for past release date tables
    table = soup.find(id="Past_branch_dates").find_parent("h2").find_next_sibling("table")
    result.update(get_version_table_dates(table))
    return result

def email_histogram_subscribers(now, notifiable_histograms, expired_histograms, dry_run = False):
    # organize histograms into buckets indexed by email
    email_histogram_names = {GENERAL_TELEMETRY_ALERT: []}
    for name, entry in notifiable_histograms:
        for email in entry.get("alert_emails", []):
            if email not in email_histogram_names: email_histogram_names[email] = []
            email_histogram_names[email].append(name)
        email_histogram_names[GENERAL_TELEMETRY_ALERT].append(name)
    if len(email_histogram_names[GENERAL_TELEMETRY_ALERT]) == 0:
        del email_histogram_names[GENERAL_TELEMETRY_ALERT]

    # send emails to users detailing the histograms that they are subscribed to that are expiring
    for email, expiring_histogram_names in email_histogram_names.items():
        expiring_list = "\n".join("* {name} expires in version {version} ({watchers}) - {description}".format(
            name=name, version=version_normalize_nightly(entry["expires_in_version"]),
            watchers="watched by {}".format(", ".join(email for email in entry["alert_emails"])) if "alert_emails" in entry else "no watchers",
            description=entry["description"]
        ) for name, entry in notifiable_histograms if name in expiring_histogram_names)
        if email != GENERAL_TELEMETRY_ALERT: # alert to a normal watcher
            email_body = """\
The following histograms will be expiring on {}, and should be removed from the codebase, or have their expiry versions updated:\n\n{}\n
This is an automated message sent by Cerberus. See https://github.com/mozilla/cerberus for details and source code.""".format(now + EMAIL_TIME_BEFORE, expiring_list)
        else: # alert to the general Telemetry alert mailing list
            expired_list = "\n".join("* {name} expired in version {version} ({watchers}) - {description}".format(
                name=name, version=version_normalize_nightly(entry["expires_in_version"]),
                watchers="watched by {}".format(", ".join(email for email in entry["alert_emails"])) if "alert_emails" in entry else "no watchers",
                description=entry["description"]
            ) for name, entry in expired_histograms)
            email_body = """\
The following histograms will be expiring on {}, and should be removed from the codebase, or have their expiry versions updated:\n\n{}\n
The following histograms are expired as of {}:\n\n{}\n
This is an automated message sent by Cerberus. See https://github.com/mozilla/cerberus for details and source code.""".format(now + EMAIL_TIME_BEFORE, expiring_list, now, expired_list)
        if dry_run:
            print("Email notification for {}:\n===============================================\n{}\n===============================================\n".format(email, email_body))
        else:
            print("Sending email notification to {} with body:\n\n{}\n".format(email, email_body))
            send_ses(FROM_ADDR, "Telemetry Histogram Expiry", email_body, email)

def is_expiring(histogram_entry, now, release_dates, include_past = False):
    """Returns `True` if the histogram `histogram_entry` is expiring on the date `now`, `False` otherwise."""
    # check if the histogram expires or not
    expiry_version = histogram_entry.get("expires_in_version", "never").strip()
    if expiry_version in {"never", "default"}: return False

    # check if the expiration version has a known release date
    expiry_version = version_normalize_nightly(expiry_version) # normalize the version to the nearest nightly if not specified
    if expiry_version in release_dates:
        return release_dates[expiry_version] <= now if include_past else release_dates[expiry_version] == now
    
    if include_past: # search for the oldest version that is greater than the current version and assume that is the release date
        sorted_versions = sorted(release_dates.keys(), cmp=version_compare)
        for version in sorted_versions:
            if version_compare(expiry_version, version) <= 0:
                return release_dates[version] <= now
    
    return False # version expires in an unknown future or past version

def get_expiring_histograms(now, release_dates, histograms, include_past = False):
    """Returns a list of pairs containing histogram names and histogram entries that are expiring, sorted alphabetically by name."""
    return sorted([
        (name, entry) for name, entry in histograms.items() if is_expiring(entry, now, release_dates, include_past=include_past)
    ], key=lambda h: h[0])

def run_tests():
    release_dates1 = {
      "38.0a1": date(2015, 6, 2),
      "39.0a1": date(2015, 6, 30),
      "40.0a1": date(2015, 8, 11),
      "41.0a1": date(2015, 9, 22),
      "42.0a1": date(2015, 11, 3),
      "43.0a1": date(2015, 12, 15),
      "44.0a1": date(2016, 1, 26),
      "45.0a1": date(2016, 3, 8),
      "46.0a1": date(2016, 4, 19),
      "47.0a1": date(2016, 5, 31),
    }
    release_dates2 = {
      "41.0a1": date(2015, 9, 22),
      "42.0a1": date(2015, 11, 3),
      "43.0a1": date(2015, 12, 15),
    }
    histograms = {
        "a": {"expires_in_version": "40"},
        "b": {"expires_in_version": "40"},
        "c": {"expires_in_version": "40.5"},
        "d": {"expires_in_version": "50"},
        "e": {"expires_in_version": "50"},
        "f": {"expires_in_version": "42"},
        "g": {"expires_in_version": "43"},
        "h": {"expires_in_version": "50a4"},
        "i": {"expires_in_version": "38"},
    }
    
    assert get_expiring_histograms(date(2015, 8, 3) + EMAIL_TIME_BEFORE, release_dates1, histograms) == []
    assert get_expiring_histograms(date(2015, 8, 4) + EMAIL_TIME_BEFORE, release_dates1, histograms) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"})]
    assert get_expiring_histograms(date(2015, 8, 5) + EMAIL_TIME_BEFORE, release_dates1, histograms) == []
    assert get_expiring_histograms(date(2015, 9, 1) + EMAIL_TIME_BEFORE, release_dates2, histograms) == []
    assert get_expiring_histograms(date(2015, 10, 26) + EMAIL_TIME_BEFORE, release_dates2, histograms) == []
    assert get_expiring_histograms(date(2015, 10, 27) + EMAIL_TIME_BEFORE, release_dates2, histograms) == [("f", {"expires_in_version": "42"})]
    assert get_expiring_histograms(date(2015, 10, 28) + EMAIL_TIME_BEFORE, release_dates2, histograms) == []
    
    assert get_expiring_histograms(date(2015, 8, 3) + EMAIL_TIME_BEFORE, release_dates1, histograms, True) == [("i", {"expires_in_version": "38"})]
    assert get_expiring_histograms(date(2015, 8, 4) + EMAIL_TIME_BEFORE, release_dates1, histograms, True) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"}), ("i", {"expires_in_version": "38"})]
    assert get_expiring_histograms(date(2015, 8, 5) + EMAIL_TIME_BEFORE, release_dates1, histograms, True) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"}), ("i", {"expires_in_version": "38"})]
    assert get_expiring_histograms(date(2015, 9, 1) + EMAIL_TIME_BEFORE, release_dates2, histograms, True) == []
    assert get_expiring_histograms(date(2015, 10, 26) + EMAIL_TIME_BEFORE, release_dates2, histograms, True) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"}), ("c", {"expires_in_version": "40.5"}), ("i", {"expires_in_version": "38"})]
    assert get_expiring_histograms(date(2015, 10, 27) + EMAIL_TIME_BEFORE, release_dates2, histograms, True) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"}), ("c", {"expires_in_version": "40.5"}), ("f", {"expires_in_version": "42"}), ("i", {"expires_in_version": "38"})]
    assert get_expiring_histograms(date(2015, 10, 28) + EMAIL_TIME_BEFORE, release_dates2, histograms, True) == [("a", {"expires_in_version": "40"}), ("b", {"expires_in_version": "40"}), ("c", {"expires_in_version": "40.5"}), ("f", {"expires_in_version": "42"}), ("i", {"expires_in_version": "38"})]

    print "All tests passed!"
    sys.exit()

def print_help():
    print "Emails subscribed users about expiring histograms."
    print "Usage: {} list|email|test".format(sys.argv[0])
    print "  {} preview [YYYY-MM-DD] output notification messages for histograms that are soon expiring as of YYYY-MM-DD (defaults to current date)".format(sys.argv[0])
    print "  {} email [YYYY-MM-DD]   notify users of histograms that are soon expiring as of YYYY-MM-DD (defaults to current date)".format(sys.argv[0])
    print "  {} test                 run various internal tests".format(sys.argv[0])

def main():
    if not (2 <= len(sys.argv) <= 3) or sys.argv[1] not in {"preview", "email", "test"}:
        print_help()
        sys.exit(1)
    if sys.argv[1] == "test": run_tests()

    # get the reference date
    now = date.today()
    if len(sys.argv) >= 3:
        try: now = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
        except ValueError:
            print "Unknown/invalid date: {}".format(sys.argv[2])
            print_help()
            sys.exit(1)
    else:
        now = date.today()
    
    # get a list of histograms that are expiring and net yet notified about, sorted alphabetically
    with open(HISTOGRAMS_FILE) as f: histograms = json.load(f)
    release_dates = get_release_dates()
    notifiable_histograms = get_expiring_histograms(now + EMAIL_TIME_BEFORE, release_dates, histograms)
    expired_histograms = get_expiring_histograms(now, release_dates, histograms, include_past=True)
    if sys.argv[1] == "preview":
        email_histogram_subscribers(now, notifiable_histograms, expired_histograms, dry_run = True)
    else: # send out emails
        email_histogram_subscribers(now, notifiable_histograms, expired_histograms)

if __name__ == "__main__":
    main()
