#!/usr/bin/python
# Reads a mail from stdin and saves it as a string.
# Then the mail is parsed analyzed and uploaded to the CouchDB given in config.py
# Give the command line arg "--override" to make this script override old an
# mail with the same hash if it existed.
# Writes log output to config.errorlog
# Saves mail in case of failed upload to config.backupdir (see error log for more info)

import sys, os, random
import common, logging, traceback
import email.parser, email.message, email.utils, itertools
import hashlib, time, calendar
import requests, json

import labels
# Import information about couchdb 
import config

class MailParserException(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

def parsemail(mail, logger='none'):
  log = logging.getLogger(logger)
  if len(mail) == 0:
    raise MailParserException('Empty mail')
  
  data = { 'type': 'mail' }
  
  # parse mail
  message = email.parser.Parser().parsestr(mail)
  
  # test defects and try to save defect mails
  if len(message.defects) != 0:
    raise MailParserException("Parser signaled defect:\n  %s" % (str(message.defects)))
  
  # encoded word is not decoded here, because it only should appear in the
  #   display name that is discarded by the last map function
  # parse from and sender addresses
  addresses = itertools.chain(*(message.get_all(field) for field in ('from', 'sender') if message.has_key(field)))
  data['from'] = map(lambda adrs: adrs[1], set(email.utils.getaddresses(addresses)))
  log.info("From: %s"%(' '.join(data['from'])))
  # parse recipient addresses
  addresses = itertools.chain(*(message.get_all(field) for field in ('to', 'cc') if message.has_key(field)))
  data['to'] = map(lambda adrs: adrs[1], set(email.utils.getaddresses(addresses)))
  log.info("To: %s"%(' '.join(data['to'])))
  
  # parse date and convert it to standard format in UTC
  if message.get('Date', None):
    try:
      # guesses format and parses 10-tuple
      parsedtime = email.utils.parsedate_tz(message.get('Date'))
      # seconds since epoch
      utc_timestamp = calendar.timegm(parsedtime[0:9])-parsedtime[9]
      # formatted
      data['date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(utc_timestamp))
      log.info("Date: %s", data['date'])
    except Exception as e:
      raise MailParserException("Could not convert %s to YYYY-MM-DD hh:mm:ss\n  %s" % (message.get('Date'), str(e)))
  
  # format current UTC time
  data['upload_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
  log.info("upload-date: %s", data['upload_date'])
  
  # add labels
  data['labels'] = []
  if message.get('Status', None):
   if not 'R' in message.get('Status'):
     data['labels'].append('unread')
  else: data['labels'].append('unread')
  
  if config.autolabels:
    labeller = labels.Labeller(path=config.autolabels)
    labeller.check(data)
  log.info("Labels: %s", ' '.join(data['labels']))
  
  return data

# Raises an IOError if something goes wrong.
def upload(docid, metadata, mail=None, override=False, preserve=True, logger='none'):
  log = logging.getLogger(logger)
  # Retrieve rev if override is enabled
  oldrevision = ''
  if override:
    r = requests.get(config.couchdb_url+docid
        , auth=config.couchdb_auth, verify=False)
    log.info(('GET', r.status_code, r.url))
    if r.status_code != 200:
      raise IOError("Query failed, code %d:\n  %s\n  %s" % (r.status_code, r.url, r.text))
    rev = json.loads(r.headers.get('etag', '""'))
    if rev != '':
      oldrevision = '?rev='+rev
      # preserve attachment
      oldmetad = json.loads(r.text)
      metadata['_attachments'] = oldmetad['_attachments']
      if preserve:
        # preserve unread status
        if 'unread' in oldmetad['labels']:
          # add 'unread' to labels list
          if 'unread' not in metadata['labels']:
            metadata['labels'].append('unread')
            log.info("preserving label 'unread' (now present)")
        else:
          # remove 'unread' from labels list
          prelen = len(metadata['labels'])
          metadata['labels'] = [x for x in metadata['labels'] if x != 'unread']
          if prelen != len(metadata['labels']): log.info("preserving label 'unread' (now not present)")
        # preserve sent flag
        if 'sent' in oldmetad['labels']:
          # add 'sent' to labels list
          if 'sent' not in metadata['labels']:
            metadata['labels'].append('sent')
            log.info("preserving label 'sent' (now present)")
            if prelen != len(metadata['labels']): log.info("preserving label 'sent' (now not present)")
        else:
          # remove 'sent' from labels list
          prelen = len(metadata['labels'])
          metadata['labels'] = [x for x in metadata['labels'] if x != 'sent']
    else: override=False
  
  if mail == None and override == False:
    raise IOError("Could not write metadata without real mail as attachment.")
  if override: log.info("Overriding old mail %s", docid)
  
  # upload meta data
  # verify=False is for untrusted SSL certificates (you created on your own)
  r = requests.put(config.couchdb_url+docid+oldrevision
      , auth=config.couchdb_auth, verify=False, data=json.dumps(metadata))
  log.info(('PUT', r.status_code, r.url))
  respjson = json.loads(r.text)
  if not respjson.get('ok', False):
    raise IOError("Could not upload metadata\n  doc._id: %s,\n  CouchDB response code %d, text: %s" % (docid, r.status_code, r.text))
  
  # upload original mail as attachment
  if not override and mail != None:
    r = requests.put(config.couchdb_url+docid+'/mail?rev='+respjson.get('rev')
        , headers={'content-type':'text/plain'}
        , auth=config.couchdb_auth, verify=False, data=mail)
    log.info(('PUT', r.status_code, r.url))
    respjson = json.loads(r.text)
    if not respjson.get('ok', False):
      raise IOError("Could not upload mail attachment\n  There is a mail without original message in your couchdb!\n  doc._id: %s,\n  CouchDB response code %d, text: %s" % (docid, r.status_code, r.text))

def hash_mail(mail):
  sha = hashlib.new('sha256')
  sha.update(mail)
  return sha.hexdigest()

# helper function to save mail to a file in case of an error
def save_mail(docid, mail):
  randomness = ''.join(random.choice('abcdef0123456789') for x in range(10))
  filename = os.path.expanduser("%s%s_%s" % (config.backupdir, docid[:10], randomness))
  f = open(filename, 'w+')
  f.write(mail)
  f.close()
  logging.getLogger('savemail').error("Written mail %s\n  to %s", docid, filename)

def main():
  ilog = logging.getLogger('stderr')
  elog = logging.getLogger('upload')
  mail = sys.stdin.read()
  # hash mail for document id
  hexdigest = hash_mail(mail)
  ilog.info("Mail received: %s", hexdigest)
  
  try:
    data = parsemail(mail, logger='stderr')
    upload(hexdigest, data, mail, "--override" in sys.argv, "--nopreserve" not in sys.argv, 'stderr')
  except:
    elog.error("Exception while parsing or uploading mail:\n %s" % traceback.format_exc())
    save_mail(hexdigest, mail)
    logging.shutdown()
    sys.exit(1)
  
  logging.shutdown()

if __name__ == '__main__': main()

