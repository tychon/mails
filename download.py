#!/usr/bin/python
# Usage:
# ./mail_download.py [--override] [--mbox FILE|--maildir DIRECTORY] [--exec CMD] [--hashes FILE] < hashes
# NOTE: Hashes is a file, where every line beginning with a hex number is a document id.
#   When the line matches this regex: ^([0-9A-Fa-f]+)\s+ the capturing part
#   has to denote a document id.
#   Comment lines out by beginning them with whitespace.
#   This is the stdout of mail_search.
# NOTE: You have to give the --override flag before --mox or --maildir
# NOTE: Most probably you have to quote your CMD:
#   $ ./mail_download.py --exec 'grep Date' < hashes
# NOTE: --exec args are run with shell=True, this is risky if you call
#   untrusted programms!

#TODO use common logging in main function

import sys, os
import common, logging
import mailbox
import re
import requests
import subprocess

import config

def download(docid=None, box=None, cmd=None, stream=None, logger='none'):
  log = logging.getLogger(logger)
  r = requests.get(config.couchdb_url+docid+'/mail'
          , auth=config.couchdb_auth, verify=False)
  log.info((r.status_code, r.url))
  mail = r.text.encode('utf8')
  if r.status_code == 200:
    if cmd != None:
      process = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
      process.communicate(mail)
      log.info("%s\n  returned with code %d" % (cmd, process.wait()))
    if box != None:
      key = box.add(mail)
      log.info("Mail saved under key %s" % key)
    if stream != None:
      stream.write(mail)
  else:
    raise IOError("Request failed, status code: %d\n  URL %s\n  RESP: %s" % (r.status_code, r.url, r.text))
  return r.text

def main():
  # open mailbox and read args
  box = cmd = None
  append = True
  allhashes = None
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--override':
      if i > 1: common.err("You should give --override as first argument!")
      append = False
    elif arg == '--mbox':
      if box: err("Multiple mailboxes given.")
      i += 1
      try:
        if not append: os.remove(sys.argv[i])
      except OSError: pass
      box = mailbox.mbox(sys.argv[i])
    elif arg == '--maildir':
      if box: err("Multiple mailboxes given.")
      i += 1
      box = mailbox.Maildir(sys.argv[i])
    elif arg == '--exec':
      i += 1
      cmd = sys.argv[i]
    elif arg == '--hashes':
      i += 1
      allhashes = open(sys.argv[i], 'r').read()
    else:
      logging.getLogger('stderr').error("Unknown arg %s"%arg)
      logging.shutdown()
      sys.exit(1)
    i += 1
  
  if allhashes == None:
    allhashes = sys.stdin.read()
  
  re_id = re.compile('([0-9A-Fa-f]+)\s+')
  for count, line in enumerate(allhashes.splitlines(True)):
    mo = re_id.match(line)
    if not mo:
      common.info("Ignoring line %d: %s" % (count, line))
      continue
    docid = mo.group(1)
    if box == None and not cmd: stream = sys.stdout
    else: stream = None
    try:
      download(docid, box, cmd, stream, 'stderr')
    except IOError as e:
      common.info(str(e))
  
  if isinstance(box, mailbox.mbox): box.close()

if __name__ == '__main__': main()

