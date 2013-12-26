
# Reads a mail from stdin and saves it as a string.
# Then the mail is parsed analyzed and uploaded to the CouchDB given in config.py
# Give the command line arg "--override" to make this script override old an
# mail with the same hash if it existed.
# Writes log output to config.errorlog
# Saves mail in case of failed upload to config.backupdir (see error log for more info)

import sys, os, random
import common, logging
import email.parser, email.message
import hashlib, time
import requests, json

import parseaddr
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
  log.info("Mail received.")
  
  data = {
    'type': 'mail'
  , 'mail': mail
  }
  
  # hash mail for document id
  sha = hashlib.new('sha256')
  sha.update(mail)
  hexdigest = sha.hexdigest()
  
  # parse mail
  message = email.parser.Parser().parsestr(mail)
  
  # test defects and try to save defect mails
  if len(message.defects) != 0:
    raise MailParserException("Parser signaled defect in mail %s:\n  %s" % (hexdigest, str(message.defects)))
  
  if message.get('From', None):
    try:
      data['from'] = froms = common.uniquify(parseaddr.extract_addresses(parseaddr.parse_address_list(message.get('From'))))
    except parseaddr.AddrParserException as e:
      raise MailParserException("Couldn't parse address in From field list.\n  %s\n  From: %s" % (str(e), message.get('From')))
  
  if message.get('To', None):
    try:
      data['to'] = common.uniquify(parseaddr.extract_addresses(parseaddr.parse_address_list(message.get('To'))))
    except parseaddr.AddrParserException as e:
      raise MailParserException("Couldn't parse address in To field list.\n  %s\n  To: %s" % (str(e), message.get('To')))
  
  if message.get('Date', None):
    try:
      # parse mail send time and convert it to UTC
      data['date'] = common.convert_from_maildate(message.get('Date'))
    except Exception as e:
      raise MailParserException("Could not convert %s to YYYY-MM-DD hh:mm:ss\n  %s" % (message.get('Date'), str(e)))
  
  # format current UTC time
  data['upload_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
  
  data['labels'] = []
  if message.get('Status', None):
   if not 'R' in message.get('Status'):
     data['labels'].append('unread')
  else: data['labels'].append('unread')
  
  #TODO check gpg signed and encrypted (no verification) in extra module
  #TODO auto labeling in extra module
  
  return data

