
# Reads a mail from stdin and saves it as a string.
# Then the mail is parsed analyzed and uploaded to the CouchDB given in config.py
# Give the command line arg "--override" to make this script override old an
# mail with the same hash if it existed.
# Writes log output to config.errorlog
# Saves mail in case of failed upload to config.backupdir (see error log for more info)

import sys
import logging
import traceback
import os
import random
import email.parser
import email.message
import hashlib
import time
import json
import requests

import common
# Import information about couchdb 
import config

# Setup logging
# For possible format strings see LogRecord attributes in logging module doc
# You have to set the level to DEBUG to see any of the .info messages.
logging.basicConfig(filename=config.errorlog, format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger()

def logexception(type, value, tb):
  msg = "Exception, possible loss of data!\n %s" % ' '.join(traceback.format_exception(type, value, tb, limit=100))
  log.critical(msg)
  logging.shutdown()
  sys.exit(1)
sys.excepthook = logexception

# Read mail from stdin
mail = sys.stdin.read()
if len(mail) == 0:
  log.error("Empty mail")
  logging.shutdown()
  sys.exit(1)

logging.info("Mail received.") # not printed, unless you set logging level to debug

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

# parse command line args
override = False
for arg in sys.argv:
  if arg == "--override":
    override = True

# parse mail
message = email.parser.Parser().parsestr(mail)

# test defects and try to save defect mails
if len(message.defects) != 0:
  log.error("Parser signaled defect in mail %s:\n  %s\n  trying to save mail" % (hexdigest, str(message.defects)))
  save_mail()
  logging.shutdown()
  sys.exit(1)

if not message.get('From', None) \
or not message.get('To', None) \
or not message.get('Subject', None) \
or not message.get('Date', None) :
  log.error("Missing one or more fields of From, To, Subject and Date\n  mail hash: %s\n  trying to save mail" % hexdigest)
  save_mail()
  logging.shutdown()
  sys.exit(1)

# parse mail send time and convert it to UTC
sendtimestr = common.convert_from_maildate(message.get('Date'))

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
, 'from': message.get('From')
, 'to': message.get('To')
, 'date': sendtimestr
, 'subject': message.get('Subject')
}

# Retrieve rev if override is enabled
oldrevision = ''
if override:
  response = requests.head(config.couchdb_url+hexdigest
      , auth=config.couchdb_auth, verify=False)
  print 'HEAD', response.url
  print response.status_code
  print response.headers
  oldrevision = '?rev='+json.loads(response.headers.get('etag', '""'))
  if oldrevision != '': print "Overriding old mail!"
  print

# UPLOAD document
# verify=False is for untrusted SSL certificates (you created on your own)
response = requests.put(config.couchdb_url+hexdigest+oldrevision
    , auth=config.couchdb_auth, verify=False, data=json.dumps(data))

print 'PUT', response.url
print response.status_code
print response.text
respjson = json.loads(response.text)
if not respjson.get('ok', False):
  log.error("Could not upload metadata\n  hash: %s,\n  CouchDB response code %d, text (multiline): %s  trying to save mail" % (hexdigest, response.status_code, response.text))
  save_mail()
  logging.shutdown()
  sys.exit(1)
print

# UPLOAD original mail as attachment
response = requests.put(config.couchdb_url+hexdigest+'/mail?rev='+respjson.get('rev')
    , headers={'content-type':'text/plain'}
    , auth=config.couchdb_auth, verify=False, data=mail)

print 'PUT', response.url
print response.status_code
print response.text
respjson = json.loads(response.text)
if not respjson.get('ok', False):
  log.error("Could not upload mail attachment\n  There is a mail without original message in your couchdb!\n  hash: %s,\n  CouchDB response code %d, text (multiline): %s  trying to save mail" % (hexdigest, response.status_code, response.text))
  save_mail()
  logging.shutdown()
  sys.exit(1)

# Use ?attachments=true to GET attachments with documents base64 encoded in one request.

# everything is ok. exit.
logging.shutdown()
sys.exit(0)

