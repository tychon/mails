
import sys, os
import mailbox
import re
import requests
import subprocess

from common import info, err
import config

# open mailbox and read args
box = None
append = True
execute = None

i = 1
while i < len(sys.argv):
  arg = sys.argv[i]
  if arg == '--override':
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
    execute = sys.argv[i]
  i += 1

# download messages and add them to mailbox
re_id = re.compile('([0-9A-Fa-f]+)\s+')
for count, line in enumerate(sys.stdin):
  mo = re_id.match(line)
  if not mo:
    err("Ignoring line %d: %s" % (count, line))
    continue
  docid = mo.group(1)
  r = requests.get(config.couchdb_url+docid+'/mail'
          , auth=config.couchdb_auth, verify=False)
  info((r.status_code, r.url))
  mail = r.text.encode('utf8')
  if r.status_code == 200:
    if execute != None:
      process = subprocess.Popen(execute, stdin=subprocess.PIPE, shell=True)
      process.communicate(mail)
      info("exec return code %d" % process.wait())
    if box != None:
      key = box.add(mail)
      info("Saved under key %s" % key)
    if execute == None and box == None: print r.text
  else:
    info("WARNING: status code: %d, text: %s" % (r.status_code, r.text))

