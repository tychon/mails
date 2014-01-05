#!/usr/bin/python
# usage: ./read.py (mbox|Maildir) (FILE|DIR) 'CMD'
# Execute CMD for every mail in mbox/Maildir given by FILE.
# Example: ./read.py mbox ~/sent 'grep ^Date:'

import sys, subprocess
import common, logging
import mailbox

def main():
  log = logging.getLogger('stderr')
  if len(sys.argv) != 4:
    common.fatal("Not enough arguments. Give 3.")
  
  if sys.argv[1] == 'mbox': box = mailbox.mbox(sys.argv[2], create=False)
  elif sys.argv[1] == 'Maildir': box = mailbox.Maildir(sys.argv[2])
  else:
    common.fatal("Unknown arg 1: %s"%sys.argv[1])
  log.info("Number of mails: %d" % box.__len__())
  
  cmd = sys.argv[3]
  for key in box.iterkeys():
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
    process.communicate(box.get_string(key))
    log.info("For mail %d\n%s\nreturned with code %d" % (key, cmd, process.wait()))
  
  logging.shutdown()
  sys.exit(0)

if __name__ == '__main__': main()
