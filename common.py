
import sys
import logging
import traceback
import time
import datetime
import re

import config

#### globally setup logging
# A logger with no handlers
logging.getLogger('none').addHandler(logging.NullHandler())
logging.getLogger('none').propagate = False
logging.getLogger('stderr').addHandler(logging.StreamHandler(sys.stderr))
logging.getLogger('stderr').propagate = False
logging.getLogger('stderr').setLevel(logging.INFO)
# Configs for all other loggers:
# For possible format strings see LogRecord attributes in logging module doc
# You have to set the level to DEBUG to see any of the .info messages.
logging.basicConfig(filename=config.errorlog, format='%(asctime)s %(levelname)s: %(message)s')
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stderr))
# Called for uncaught exceptions
def logexception(type, value, tb):
  msg = "Exception, possible loss of data!\n %s" % ' '.join(traceback.format_exception(type, value, tb, limit=100))
  logging.getLogger().critical(msg)
  logging.shutdown()
  sys.exit(1)
sys.excepthook = logexception

# Write info to stderr
def info(msg):
  if type(msg) == str: sys.stderr.write(msg)
  else: sys.stderr.write(repr(msg))
  sys.stderr.write('\n')
# Write message to logger 'stderr' and exit with code 1
def fatal(msg, logger='stderr'):
  if type(msg) == str: logging.getLogger(logger).error(msg)
  else: logging.getLogger(logger).error(repr(msg))
  logging.shutdown()
  sys.exit(1)

# see http://stackoverflow.com/a/480227
# Make all elements in an iterable object unique.
# Returns a list.
def uniquify(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

