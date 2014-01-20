
import sys, logging, traceback
import requests, json
import config

#### globally setup logging
# A logger with no handlers
logging.getLogger('none').addHandler(logging.NullHandler())
logging.getLogger('none').propagate = False
logging.getLogger('stderr').addHandler(logging.StreamHandler(sys.stderr))
logging.getLogger('stderr').propagate = False
logging.getLogger('stderr').setLevel(config.loglevel)
# Configs for all other loggers:
# For possible format strings see LogRecord attributes in logging module doc
# You have to set the level to DEBUG to see any of the .info messages.
logging.basicConfig(filename=config.errorlog, format='%(asctime)s %(levelname)s: %(message)s')
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stderr))
logging.getLogger().setLevel(config.errorloglevel)
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

# Test mail metadata for equality: .type .date .from .to .labels
# Requires all fields to be present
def eq_mail_meta(doca, docb):
  def eq(field, fun):
    if field in doca and field in docb:
      return fun(doca[field], docb[field])
    if field not in doca and field not in docb:
      return True
    return False
  if (not eq('type', str.__eq__) or
      not eq('date', str.__eq__) or
      not eq('from', list.__eq__) or
      not eq('to', list.__eq__) or
      not eq('labels', list.__eq__)): return False
  else: return True

#################
# requests helper

def get_doc(docid, errmsg='', logger='none', parsejson=True):
  log = logging.getLogger(logger)
  r = requests.get("%s%s"%(config.couchdb_url, docid)
          , auth=config.couchdb_auth, verify=False)
  log.debug(('GET', r.status_code, r.url))
  if not r.status_code == 200:
    raise IOError("%s\nHTTP code %d:\n%s\n%s"
        %(errmsg, r.status_code, r.url, r.text))
  if parsejson: return json.loads(r.text)
  else: return r.text

def get_view(viewname, errmsg='', logger='none'):
  log = logging.getLogger(logger)
  r = requests.get('%s%s_view/%s'%(config.couchdb_url, config.design_doc, viewname)
          , auth=config.couchdb_auth, verify=False)
  log.debug(('GET', r.status_code, r.url))
  if not r.status_code == 200:
    raise IOError("%s\nHTTP code %d:\n%s\n%s"
        % (errmsg, r.status_code, r.url, r.text))
  res = json.loads(r.text)
  return (res['total_rows'], [x['id'] for x in res['rows']])

