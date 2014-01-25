#!/usr/bin/env python

import sys
import common, logging
import requests, json
import subprocess

import config

# Initiate bidirectional continuous
# replication by commiting documents to
# replicator database.
def setup_continuous_sync(logger='stderr'):
  log = logging.getLogger(logger)
  
  s = requests.Session()
  s.auth = config.couchdb_auth
  s.headers.update({'content-type':'application/json'})
  s.verify = False
  
  # do LOCAL -> REMOTE
  log.info("Initiating LOCAL -> REMOTE ...")
  repldata = {
    'source': config.couchdb_url
  , 'target': config.remotedb_url
  , 'continuous': True
  }
  r = s.post(config.replicator_url, data=json.dumps(repldata))
  log.info("%s\nreturn code: %d\n%s\n"%(r.url, r.status_code, r.text) )
  if r.status_code != 200 and r.status_code != 201:
    raise IOError("Could not replicate LOCAL -> REMOTE: %d\n  %s\n%s"%(r.status_code, r.url, r.text))
  
  # do REMOTE -> LOCAL
  log.info("Initiating REMOTE -> LOCAL ...")
  repldata = {
    'source': config.remotedb_url
  , 'target': config.couchdb_url
  , 'continuous': True
  }
  r = s.post(config.replicator_url, data=json.dumps(repldata))
  log.info("%s\nreturn code: %d\n%s\n"%(r.url, r.status_code, r.text) )
  if r.status_code != 200 and r.status_code != 201:
    raise IOError("Could not replicate REMOTE -> LOCAL: %d\n  %s\n%s"%(r.status_code, r.url, r.text))

# Do one shot replication, may be useful sometimes.
# Use with --sync
def one_shot_sync(logger='stderr'):
  log = logging.getLogger(logger)
  
  s = requests.Session()
  s.auth = config.couchdb_auth
  s.headers.update({'content-type':'application/json'})
  s.verify = False
  
  # do LOCAL -> REMOTE
  log.info("Replicating LOCAL -> REMOTE ...")
  repldata = {
    'source': config.couchdb_url
  , 'target': config.remotedb_url
  }
  r = s.post(config.replicate_url, data=json.dumps(repldata))
  log.debug( (r.url, r.status_code, r.text) )
  if r.status_code != 200 and r.status_code != 201:
    raise IOError("Could not replicate LOCAL -> REMOTE: %d\n  %s\n%s"%(r.status_code, r.url, r.text))
  
  # do REMOTE -> LOCAL
  log.info("Replicating REMOTE -> LOCAL ...")
  repldata = {
    'source': config.remotedb_url
  , 'target': config.couchdb_url
  }
  r = s.post(config.replicate_url, data=json.dumps(repldata))
  log.debug( (r.url, r.status_code, r.text) )
  if r.status_code != 200 and r.status_code != 201:
    raise IOError("Could not replicate REMOTE -> LOCAL: %d\n  %s\n%s"%(r.status_code, r.url, r.text))



def get_current_updateseq(logger='stderr'):
  log = logging.getLogger(logger)
  r = requests.get('%s_changes?descending=true&limit=1'%config.couchdb_url,
          auth=config.couchdb_auth, verify=False)
  return int(json.loads(r.text)['last_seq'])

def listen(callback, since=None, logger='stderr'):
  log = logging.getLogger(logger)
  if not since: since = get_current_updateseq(logger)
  log.info("Listening for changes since seq %d ..."%since)
  r = requests.get('%s_changes?since=%s&feed=continuous&heartbeat=50000&include_docs=true'
              %(config.couchdb_url, since),
          auth=config.couchdb_auth, verify=False, stream=True)
  log.debug( (r.url, r.status_code, r.headers) )
  if r.status_code != 200:
    raise IOError("Could not GET: code %s\n  %s\n%s"%(r.status_code, r.url, r.text))
  for line in r.iter_lines(chunk_size=1):
    if line: callback(json.loads(line))

def handle_update(seqobj, logger='stderr'):
  log = logging.getLogger(logger)
  if seqobj.get('deleted', None):
    # mail deleted
    cmd = config.deleted_mail_cmd
  else:
    doc = seqobj['doc']
    if doc.get('type', '') == 'mail':
      if doc['_rev'].startswith('1-'):
        # new mail
        cmd = config.new_mail_cmd
      else: # mail changed
        cmd = config.changed_mail_cmd
    else: return
  if not cmd: return
  cmd = cmd.replace('{docid}', seqobj['doc']['_id'])
  log.info(cmd)
  subprocess.Popen(cmd, shell=True)
    
def main():
  # parse args
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--setup-continuous':
      setup_continuous_sync()
      return
    elif arg == '--sync':
      one_shot_sync()
      return
    else:
      common.fatal("Unknown argument: %s"%arg)
    i += 1
  
  listen(handle_update)

if __name__ == '__main__': main()

