#!/usr/bin/python
# Usage:
# ./mail_download.py [--docs FILE] [< FILE]

import sys, os, traceback
import common, logging
import requests, re

import config

def delete(docid, logger='stderr'):
  # get old rev
  olddoc = common.get_doc(docid, errmsg='Could not fetch old revision.', logger=logger)
  # delete
  log = logging.getLogger(logger)
  r = requests.delete(config.couchdb_url+docid+'?rev='+olddoc['_rev'],
          auth=config.couchdb_auth, verify=False)
  log.debug( (r.status_code, r.url, r.text) )
  if r.status_code != 200:
    raise IOError("Could not delete %s revision %s: %d\n  %s\n%s"
        %(docid, olddoc['_rev'], r.status_code, r.url, r.text))

def main():
  log = logging.getLogger('stderr')
  # open mailbox and read args
  allids = None
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--docs':
      i += 1
      allids = open(sys.argv[i], 'r').read()
    else:
      common.fatal("Unknown arg %s"%arg)
    i += 1
  
  if allids == None:
    allids = sys.stdin.read()
  
  re_id = re.compile('([0-9A-Fa-f]+)\s+')
  for count, line in enumerate(allids.splitlines(True)):
    mo = re_id.match(line)
    if not mo:
      log.info("Ignoring line %d: %s" % (count, line))
      continue
    docid = mo.group(1)
    # (do not except Exceptions: they should go into error log)
    delete(docid, 'stderr')
    log.info("Deletion successful: %s"%docid)

if __name__ == '__main__': main()

