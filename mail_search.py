
import sys
import requests
import json

import config

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
  elif arg == "-date":
    i += 1
    hdate = sys.argv[i]
  i += 1

res = None

#TODO make case insensitive

# Do from request
if hfrom:
  r = requests.get(config.couchdb_url+config.design_doc+('_view/from?startkey="%s"&endkey="%s\u9999"' % (hfrom, hfrom))
          , auth=config.couchdb_auth, verify=False)
  print r.url
  print r.status_code
  if not r.status_code == 200:
    print "Query failed"
    print r.text
    sys.exit(1)
  res = json.loads(r.text)['rows']
  if len(res) == 0:
    print "No results for FROM: %s*" % (hfrom)
    sys.exit(0)
  print "%s results for FROM: %s*" % (len(res), hfrom)
  res = map(lambda x: x['value'], res)

if hto:
  if res:
    # Search for to in res
    res = filter(lambda doc: bool(filter(lambda addr: addr.startswith(hto), doc['to'])), res)
  else:
    # Search for to in CouchDB
    r = requests.get(config.couchdb_url+config.design_doc+('_view/to?startkey="%s"&endkey="%s\u9999"' % (hto, hto))
            , auth=config.couchdb_auth, verify=False)
    print r.url
    print r.status_code
    if not r.status_code == 200:
      print "Query failed"
      print r.text
      sys.exit(1)
    res = json.loads(r.text)['rows']
    res = map(lambda x: x['value'], res)
  
  if len(res) == 0:
    print "No results for TO: %s*" % (hto)
    sys.exit(0)
  print "%s results for TO: %s*" % (len(res), hto)

#TODO filter by other criteria

print "\nRESULT"
for val in res: print val['_id']

