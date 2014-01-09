#!/usr/bin/python

import sys, common, logging, requests, json
import config, download, upload

def main():
  log = logging.getLogger('stderr')
  docid = None
  dryrun = False
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--docid':
      i += 1
      docid = sys.argv[i]
    if arg == '--dry':
      i += 1
      dryrun = True
    else:
      common.fatal("Unknown arg %s"%arg)
    i += 1
  
  docids = []
  if docid: docids = [docid]
  else:
    _, docids = common.get_view('conflicts', logger='stderr')
  
  log.info("Number of conflicts to solve: %d"%len(docids))
  
  for docnum, docid in enumerate(docids):
    print "\n### Document %d of %d"%(docnum, len(docids))
    ## download all revisions of document:
    revs = []
    # couchdbs deterministic winnning revision:
    winningdoc = common.get_doc("%s?conflicts=true"%docid, logger='stderr')
    revs.append(winningdoc)
    # other revisions
    for rev in winningdoc['_conflicts']:
      doc = common.get_doc("%s?rev=%s"%(docid, rev), logger='stderr')
      revs.append(doc)
    log.info("Revisions: %d"%len(revs))
    ## print revisions
    for revnum, rev in enumerate(revs):
      print "# Revision no. %d"%(revnum+1)
      print rev['_rev']
      print "Date: %s UTC Upload Date: %s UTC"%(rev.get('date', None), rev.get('upload_date', None))
      print "From: %s"%' '.join(rev.get('from', ['NONE']))
      print "To: %s"%' '.join(rev.get('to', ['NONE']))
      print "Labels: %s"%' '.join(rev.get('labels', ['NONE']))
    # ask user for preferred revision
    revno = -1
    while revno == -1:
      sys.stdout.write("# Decide now (s for skip): ")
      revno = raw_input()
      if revno == 's': break
      try: revno = int(revno)
      except ValueError:
        print "You jester. A number please!"
        revno = -1
        continue
      if revno < 1 or revno > len(revs):
        print "Give a number between 1 to %d (both inclusive)"%len(revs)
        revno = -1
    else:
      # create bulk doc data
      bulk = []
      for revnum, rev in enumerate(revs):
        if revnum != revno-1: rev['_deleted'] = True
        bulk.append(rev)
      bulkdata = json.dumps({'docs':bulk})
      log.debug(bulkdata)
      if dryrun:
        print "If this weren't a dry run, I would have updated %d documents now."%len(bulk)
      else:
        print "Uploading changes ..."
        r = requests.post("%s/_bulk_docs"%(config.couchdb_url)
                , auth=config.couchdb_auth, verify=False, data=bulkdata
                , headers = {'content-type': 'application/json'})
        log.debug(('PUT', r.status_code, r.url))
        if not r.status_code == 201:
          raise IOError("Could not upload documents\n  %s\n  CouchDB response code %d, text: %s\nPUT Data:\n%s" % (r.url, r.status_code, r.text, bulkdata))
  
  logging.shutdown()
  sys.exit(0)

if __name__ == '__main__': main()

