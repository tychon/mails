
import sys, logging
import requests, json

import common
import config

# May return an empty list, but not None.
def search(hfrom=None, hto=None, since=None, before=None, logger='none'):
  log = logging.getLogger(logger)
  res = None
  
  # Do From:
  if hfrom:
    r = requests.get(config.couchdb_url+config.design_doc+('_view/from?startkey="%s"&endkey="%s\u9999"' % (hfrom, hfrom))
            , auth=config.couchdb_auth, verify=False)
    log.info((r.status_code, r.url))
    if not r.status_code == 200:
      raise IOError("Query failed, code %d:\n  %s\n  %s" % (r.status_code, r.url, r.text))
    res = json.loads(r.text)['rows']
    if len(res) == 0:
      log.info("No results for From: %s*", hfrom)
      return []
    log.info("%s results for From: %s*", len(res), hfrom)
    res = map(lambda x: x['value'], res)
  
  # Do To:
  if hto:
    if res:
      # Search for to in res
      res = filter(lambda doc: bool(filter(lambda addr: addr.startswith(hto), doc['to'])), res)
    else:
      # Search for to in CouchDB
      r = requests.get(config.couchdb_url+config.design_doc+('_view/to?startkey="%s"&endkey="%s\u9999"' % (hto, hto))
              , auth=config.couchdb_auth, verify=False)
      log.info((r.status_code, r.url))
      if not r.status_code == 200:
        raise IOError("Query failed, code %d:\n  %s\n  %s" % (r.status_code, r.url, r.text))
      res = json.loads(r.text)['rows']
      res = map(lambda x: x['value'], res)
    
    if len(res) == 0:
      log.info("No results for To: %s*", hto)
      return []
    log.info("%s results for To: %s*", len(res), hto)
  
  #TODO filter by other criteria
  
  if not res: return []
  return res

def main():
  # parse args
  hto = None
  hfrom = None
  hdate = None
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == "-to":
      i += 1
      hto = sys.argv[i]
    elif arg == "-from":
      i += 1
      hfrom = sys.argv[i]
    else:
      err("unknown arg %s" % arg)
      sys.exit(1)
    i += 1
  res = search(hfrom, hto, logger='stderr')
  for val in res: print val['_id']

if __name__ == '__main__': main()

