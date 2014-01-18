#!/usr/bin/python
# options:
# --docs FILE
# --nopres_unread

#TODO option --verbose to print output of upload.pasemail and other stuff
# instead of only dots

import sys, common, logging, re, requests, json
import config, download, upload

def main():
  log = logging.getLogger('stderr')
  docidsraw = None
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--docs':
      i += 1
      docidsraw = open(sys.argv[i], 'r').read()
    i += 1
  
  # download list of ids
  if docidsraw:
    ids = []
    re_id = re.compile('([0-9A-Fa-f]+)\s+')
    for count, line in enumerate(docidsraw.splitlines(True)):
      mo = re_id.match(line)
      if not mo:
        log.info("Ignoring line %d: %s" % (count, line))
        continue
      ids.append(mo.group(1))
  else: # all documents
    _, ids = common.get_view('all_mails')
  
  log.info("Reprocessing %d documents."%len(ids))
  for docid in ids:
    sys.stdout.write('.')
    doc = common.get_doc(docid)
    mail = download.download(docid)
    
    if '--reparsemeta':
      newdoc = upload.parsemail(mail)
    
    if doc != newdoc:
      upload.upload(docid, newdoc, override=True
          , preserveread=('--nopres_unread' not in sys.argv))
    sys.stdout.flush()
  
  logging.shutdown()
  sys.exit(0)

if __name__ == '__main__': main()

