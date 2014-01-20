#!/usr/bin/python
# options:
# --verbose Print more output to stderr, try config.loglevel too!
# --docs FILE
# If none of the following options is given, the unread status is preserved
# as in the database and the only information NOT overwritten.
# --nopres_unread Use read status as in input document
# --read Mark all as read (delete 'unread')
# --unread Mark all as unread (add 'unread')

import sys, common, logging, re, requests, json
import config, download, upload

def main():
  log = logging.getLogger('stderr')
  docidsraw = None
  unreadmode = None
  verbose=False
  
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--docs':
      i += 1
      docidsraw = open(sys.argv[i], 'r').read()
    elif arg == '--verbose':
      verbose = True
    elif arg == '--nopres_unread':
      if unreadmode: common.fatal("Choose one and only one unread-labelling-mode.")
      unreadmode = 'nopres_unread'
    elif arg == '--read':
      if unreadmode: common.fatal("Choose one and only one unread-labelling-mode.")
      unreadmode = 'read'
    elif arg == '--unread':
      if unreadmode: common.fatal("Choose one and only one unread-labelling-mode.")
      unreadmode = 'unread'
    else:
      common.fatal("Unknown arg: %s"%arg)
    i += 1
  if not unreadmode: unreadmode == 'preserve'
  
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
  if verbose: uploadlogger = 'stderr'
  else: uploadlogger = 'none'
  for docid in ids:
    if not verbose: sys.stdout.write('.')
    doc = common.get_doc(docid, logger=uploadlogger)
    mail = download.download(docid, logger=uploadlogger)
    newdoc = upload.parsemail(mail, logger=uploadlogger)
    
    preserveunread = True
    if unreadmode == 'unread' or unreadmode == 'read':
      upload.preserve_unread(newdoc, unreadmode, logger=uploadlogger)
      preserveunread = False
    elif unreadmode == 'nopres_unread':
      preserveunread = False
    
    if doc != newdoc:
      upload.upload(docid, newdoc, override=True
          , preserveread=preserveunread, logger=uploadlogger)
    if not verbose: sys.stdout.flush()
  
  logging.shutdown()
  sys.exit(0)

if __name__ == '__main__': main()

