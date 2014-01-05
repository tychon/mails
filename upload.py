#!/usr/bin/python
# Reads a mail from stdin and saves it as a string.
# Then the mail is parsed analyzed and uploaded to the CouchDB given in config.py
# Give the command line arg "--override" to make this script override old an
# mail with the same hash if it existed.
# Writes log output to config.errorlog
# Saves mail in case of failed upload to config.backupdir (see error log for more info)

import sys, os, random
import common, logging, traceback
import email.parser, email.message
import hashlib, time
import requests, json

import parseaddr, labels
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
  
  if message.get('From', None):
    try:
      data['from'] = froms = common.uniquify(parseaddr.extract_addresses(parseaddr.parse_address_list(message.get('From'))))
      log.info("From: %s", ' '.join(froms))
    except parseaddr.AddrParserException as e:
      raise MailParserException("Couldn't parse address in From field list.\n  %s\n  From: %s" % (str(e), message.get('From')))
  
  if message.get('To', None):
    try:
      data['to'] = tos = common.uniquify(parseaddr.extract_addresses(parseaddr.parse_address_list(message.get('To'))))
      log.info("To: %s", ' '.join(tos))
    except parseaddr.AddrParserException as e:
      raise MailParserException("Couldn't parse address in To field list.\n  %s\n  To: %s" % (str(e), message.get('To')))
  
  if message.get('Date', None):
    try:
      # parse mail send time and convert it to UTC
      data['date'] = common.convert_from_maildate(message.get('Date'))
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
def upload(docid, metadata, mail=None, override=False, logger='none'):
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
      print r.text
      metadata['_attachments'] = json.loads(r.text)['_attachments']
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
    upload(hexdigest, data, mail, "--override" in sys.argv, 'stderr')
  except:
    elog.error("Exception while parsing or uploading mail:\n %s" % traceback.format_exc())
    save_mail(hexdigest, mail)
    logging.shutdown()
    sys.exit(1)
  
  logging.shutdown()

if __name__ == '__main__': main()

