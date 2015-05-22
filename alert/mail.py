# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import boto.ses

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

with open("aws-settings.json", "r") as f:
  settings = json.load(f)
  AWS_ACCESS_KEY = settings["AWS_ACCESS_KEY"]
  AWS_SECRET_ACCESS_KEY = settings["AWS_SECRET_ACCESS_KEY"]
  AWS_REGION = settings["AWS_REGION"]

def send_ses(fromaddr,
             subject,
             body,
             recipient,
             filename=''):
    """Send an email via the Amazon SES service.

Configuration is stored in `aws-settings.json` in the working directory, of the following form:
  {
    "AWS_ACCESS_KEY": "ACESS_KEY_GOES_HERE",
    "AWS_SECRET_ACCESS_KEY": "SECRET_ACCESS_KEY_GOES_HERE",
    "AWS_REGION": "us-west-2"
  }

Example:
  send_ses('me@example.com, 'greetings', "Hi!", 'you@example.com)

Return:
  If 'ErrorResponse' appears in the return message from SES,
  return the message, otherwise return an empty '' string."""
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = fromaddr
    msg['To'] = recipient
    msg.attach(MIMEText(body))

    if filename:
        attachment = open(filename, 'rb').read()
        part = MIMEApplication(attachment)
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(part)

    conn = boto.ses.connect_to_region(AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    result = conn.send_raw_email(msg.as_string())

    return result if 'ErrorResponse' in result else ''
