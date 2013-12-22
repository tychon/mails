
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

# Write info and err msgs to stderr
def info(msg):
  if type(msg) == str: sys.stderr.write(msg)
  else: sys.stderr.write(repr(msg))
  sys.stderr.write('\n')
def err(msg):
  if type(msg) == str: sys.stderr.write(msg)
  else: sys.stderr.write(repr(msg))
  sys.stderr.write('\n')
  sys.stderr.flush()
  sys.exit(1)

re_date = re.compile(r'([^\(]*)\(')
# Convert date from "Sat, 27 Sep 2008 22:05:46 +0200"
# to "2008-09-27 20:05:46" UTC
# In dates like 'Wed, 18 Sep 2013 19:13:14 +0200 (CEST)' the name of the
# timezone is simply ignored.
def convert_from_maildate(date):
  if '(' in date: # ignore timezone name
    date = re_date.match(date).group(1).strip()
  t = datetime.datetime.strptime(date[:-6], "%a, %d %b %Y %H:%M:%S")
  t = t + datetime.timedelta(hours=(-1 * int(date[-5:]) / 100))
  return datetime.datetime.strftime(t, "%Y-%m-%d %H:%M:%S")

# see http://stackoverflow.com/a/480227
# Make all elements in an iterable object unique.
# Returns a list.
def uniquify(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

#TODO unfold whitespace
