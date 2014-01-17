
import sys
import common, logging
import requests, json

import config

# Initiate one shot replication, since
# the changes API works only when the databases are connected.
# There may be some changes missed.
# Only for safety.
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
  repldata = {
    'source': config.remotedb_url
  , 'target': config.couchdb_url
  }
  r = s.post(config.replicate_url, data=json.dumps(repldata))
  log.debug( (r.url, r.status_code, r.text) )
  if r.status_code != 200 and r.status_code != 201:
    raise IOError("Could not replicate REMOTE -> LOCAL: %d\n  %s\n%s"%(r.status_code, r.url, r.text))

def main():
  one_shot_sync()

if __name__ == '__main__': main()

