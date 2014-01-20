#!/usr/bin/python
# usage: ./view.py [--tmp FILE] [--changed FILE] [--upload] [--sent FILE] [--docs FILE] [--search QUERY]
#   --verbose      Print more output to logger, try config.loglevel too!
#   --docs FILE    A file with the hashes of the documents to load
#   --search QUERY Do a search and view all results. Asks, when there are more than 100 results.
#   --tmp FILE     A temporary file used to save downloaded mails. Given to mutt with -f
#                  An existing file with this name will be overwritten.
#   --muttrc FILE  A file given to mutt with -F
#   --sent FILE    A mbox used by mutt to save sent mails (muttrc: set record="$HOME/Mail/sent";)
#                  The mails are uploaded to database independent of --changed and --upload
#   --changed FILE A File to save changed hashes to (one hash per line)
#   --upload       Upload changed mail (Overriding mail metadata in database including 'read' label)
#   --sent         Upload sent mail
# Mutt breaks, if you give some stdin to this script.

import sys, os, re, subprocess, traceback
import common, logging
import search, lrparsing
import mailbox, hashlib

import config
import download, upload

def hash_mails(box):
  hashes = []
  for key in box.iterkeys():
    hashes.append( ( key, upload.hash_mail(box.get_string(key)) ) )
  return hashes

def main():
  log = logging.getLogger('stderr')
  elog = logging.getLogger('view') # error logger
  
  # here is the contents of the doc ids file saved,
  # if its given with --docs
  allhashes = ''
  squery = None
  
  # load defaults
  muttrc = config.muttrc
  boxpath = config.temp_mailbox
  sentpath = config.sent_mailbox
  changedhashesfile = None
  doupload = False
  verbose = False
  uploadsent = False
  
  # load command line args
  i = 1
  while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '--docs':
      i += 1
      allhashes = open(sys.argv[i], 'r').read()
    elif arg == '--verbose':
      verbose = True
    elif arg == '--tmp':
      i += 1
      boxpath = sys.argv[i]
    elif arg == '--muttrc':
      i += 1
      muttrc = sys.argv[i]
    elif arg == '--sent':
      i += 1
      sentpath = sys.argv[i]
    elif arg == '--changed':
      i += 1
      changedhashesfile = sys.argv[i]
    elif arg == '--upload':
      doupload = True
    elif arg == '--sent':
      uploadsent = True
    elif arg == '--search':
      i+= 1
      squery = sys.argv[i]
    else:
      common.fatal("Unknown arg %s"%arg)
    i += 1
  
  if squery and allhashes:
    common.fatal("Arguments --docs and --search are exclusive!")
  if not squery and not allhashes:
    common.fatal("No documents given. Try --docs FILE or --search QUERY .")
  
  # open temporary mailbox
  if boxpath == None:
    common.fatal("No temporary mailbox given.")
  boxpath = os.path.expanduser(boxpath)
  log.debug("Using temporary mailbox: %s"%boxpath)
  # try to delete old temporary mailbox
  try: os.remove(boxpath)
  except OSError: pass
  # open
  box = mailbox.mbox(boxpath)
  
  if muttrc: muttrc = '-F '+muttrc
  else: muttrc = ''
  
  if allhashes:
    ids = []
    # read hashes
    re_id = re.compile('([0-9A-Fa-f]+)\s+')
    for count, line in enumerate(allhashes.splitlines(True)):
      mo = re_id.match(line)
      if mo == None:
        log.info("Ignoring line %d: %s" % (count+1, line))
        continue
      docid = mo.group(1)
      ids.append(docid)
  if squery:
    try:
      ids = search.search(squery, 'stderr')
    except lrparsing.ParseError:
      common.fatal("Could not parse query:\n%s\n%s"%(squery, traceback.format_exc()))
    except IOError:
      common.fatal(traceback.format_exc())
  if len(ids) == 0:
    common.fatal("No documents found.")
  if len(ids) > 100:
    sys.stdout.write("Download %d mails? (y/n): "%len(ids))
    resp = raw_input()
    if resp.lower() != 'y' and resp.lower() != 'yes':
      common.fatal("OK. Exit.")
  
  # download docs
  log.info("Downloading %d mails."%len(ids))
  for doc in ids:
    try: download.download(doc, box=box, logger='stderr')
    except IOError as e:
      common.fatal("Couldnt download mail %s\n  %s" % (docid, traceback.format_exc(e)))
  
  if len(ids) != box.__len__():
    common.fatal("Something strange happened. Not enough mails in mailbox!")
  
  hashes_before = hash_mails(box)
  box.close()
  
  # open mutt
  cmd = "mutt %s -f %s" % (muttrc, boxpath)
  log.info(cmd)
  retval = subprocess.call(cmd, shell=True)
  log.info("Mutt returned with status %d."%retval)
  if retval:
    common.fatal("Mutt error %d. EXIT. No changes to DB"%retval)
  
  box = mailbox.mbox(boxpath)
  # detect changes in mbox
  hashes_after = hash_mails(box)
  
  if len(hashes_before) != len(hashes_after) or len(hashes_before) != len(ids):
    common.fatal("Some mails were deleted (or added). Aborting. No changes made to DB.")
  
  # filter differing hashes
  changed = filter(lambda pair: pair[1] != pair[2], zip(ids, hashes_before, hashes_after))
  # get (mbox key, docid) only
  changed = map(lambda pair: (pair[1][0], pair[0]), changed)
  log.info("%d mails changed."%len(changed))
  
  # write changed mails file
  if changedhashesfile:
    f = open(changedhashesfile, 'w+')
    for key, docid in changed:
      f.write(docid)
      f.write('\n')
    f.close()
  
  if verbose: uploadlogger = 'stderr'
  else: uploadlogger = 'none'
  
  # upload changed mails
  if doupload:
    # TODO ask for upload?
    log.info("Uploading %d mails"%len(changed))
    for key, docid in changed:
      try:
        mdata = upload.parsemail(box.get_string(key), logger=uploadlogger)
        upload.upload(docid, mdata, override=True, preserveread=False, logger=uploadlogger)
      except:
        elog.error("Exception while parsing or uploading mail:\n %s" % traceback.format_exc())
        upload.save_mail(docid, box.get_string(key))
        logging.shutdown()
        sys.exit(1)
  box.close()
  
  # upload sent mails
  if uploadsent and  sentpath:
    # open mailbox
    sentpath = os.path.expanduser(sentpath)
    log.debug("Opening sent mailbox: %s"%sentpath)
    try:
      box = mailbox.mbox(sentpath, create=False)
    except mailbox.NoSuchMailboxError as e:
      common.fatal("Given mailbox for sent mails does not exist: %s"%sentpath)
    log.info("Uploading %d mails in sent mbox %s"%(box.__len__(), sentpath))
    # upload
    for key in box.iterkeys():
      try:
        mail = box.get_string(key)
        mdata = upload.parsemail(mail, logger=uploadlogger)
        doc_id = upload.hash_mail(mail)
        upload.upload(doc_id, mdata, mail, logger=uploadlogger)
      except:
        elog.error("Exception while parsing or uploading mail:\n %s" % traceback.format_exc())
        upload.save_mail(docid, box.get_string(key))
        continue
    box.close()
    # truncate file
    log.debug("Truncating sent mbox: %s"%sentpath)
    open(sentpath, 'w').close()
  
  logging.shutdown()
  sys.exit(0)

if __name__ == '__main__': main()

