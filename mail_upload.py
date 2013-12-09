
# Reads a mail from stdin and saves it as a string.
# Then the mail is parsed analyzed and uploaded to the CouchDB given in config.py
# Writes log output to error.log
# Saves mail in case of failed upload to config.backupdir (see error log for more info)

import sys
import logging
import os
import random
import email.parser
import email.message
import hashlib
import time
import json
import requests

# Import information about couchdb 
import config

# Setup logging
# For possible format strings see LogRecord attributes in logging module doc
# You have to set the level to DEBUG to see any of the .info messages.
logging.basicConfig(filename='error.log', format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger()

mail = sys.stdin.read()
if len(mail) is 0:
  log.error("Empty mail")
  logging.shutdown()
  sys.exit(1)

logging.info("Mail received.") # not print, unless you set logging level to debug

# hash mail for document id
sha = hashlib.new('sha256')
sha.update(mail)
hexdigest = sha.hexdigest()

# helper function to save mail to a file in case of an error
def save_mail():
  randomness = ''.join(random.choice('abcdef0123456789') for x in range(10))
  filename = os.path.expanduser("%s%s_%s" % (config.backupdir, hexdigest[:10], randomness))
  f = open(filename, 'w+')
  f.write(mail)
  f.close()
  log.error("Written mail %s\n  to %s", hexdigest, filename)

# parse mail from stdin
message = email.parser.Parser().parsestr(mail)

#TODO test defects / empty mails?
#put defect mails into special document?
print 'defects:', len(message.defects)
for defect in message.defects:
  print defect

print message.keys()


# parse mail send time and convert it to UTC TODO?
#sendtime = time.strptime(message.get('Date')[:-5], "%a, %d %b %Y %H:%M:%S")
#sendtimestr = time.strftime("%Y-%m-%d %H:%M:%S", sendtime)

# format current UTC time
nowtimestr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))

#TODO check gpg signed and encrypted (not verification) in extra module
#TODO auto labeling in extra module
#TODO create index for full text search

data = {
  'upload_date': nowtimestr
, 'flags': []
, 'labels': ['unread'] # TODO do this in autolabeling
, 'keywords': []
, 'from': message.get('From', None)
, 'to': message.get('To', None)
, 'date': message.get('Date', None)
, 'data': mail
}

# upload mail
# verify=False is for untrusted SSL certificates (you created on your own)
response = requests.put(config.couchdb_url+hexdigest
    , auth=config.couchdb_auth
    , verify=False, data=json.dumps(data))

print response.status_code
print response.text

if not response.status_code is 200:
  log.error("Could not upload mail\n  hash: %s,\n  CouchDB response code %d, text (multiline): %s\n  trying to save mail" % (hexdigest, response.status_code, response.text))
  save_mail()
  logging.shutdown()
  sys.exit(1)

# everything is ok. exit.
logging.shutdown()
python.exit(0)

