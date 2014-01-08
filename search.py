#!/usr/bin/python
import sys, logging, traceback
import requests, json

import common
import config, lrparsing
import searchqueryparser as sqp

# Returns a list of documents matching the search criteria.
# Raises lrparsing.ParseException on malformed query.
# May return an empty list, but not None.
def search(query, logger='none', verbose=False):
  log = logging.getLogger(logger)
  
  ast = sqp.parse(query) # ParseException handled by caller
  log.info("Abstract Syntax Tree:\n%s\n"%sqp.formatTree(ast))
  
  def cb_atom(name, tok, line, col):
    tok = tok.lower()
    r = requests.get(config.couchdb_url+config.design_doc
            +('_view/%s?startkey="%s"&endkey="%s\u9999"' % (name.lower(), tok, tok))
            , auth=config.couchdb_auth, verify=False)
    log.debug((r.status_code, r.url))
    if not r.status_code == 200:
      raise IOError("line %d col %d: %s %s: Query failed, code %d:\n  %s\n  %s"
          % (line, col, name, tok, r.status_code, r.url, r.text))
    res = json.loads(r.text)['rows']
    if verbose:
      for row in res: print '   ',row['id'],row['key']
    res = map(lambda x: x['id'], res)
    if len(res) == 0: log.info("%s %s* (no results)", name, tok)
    else: log.info("%s %s* (%d results)", name, tok, len(res))
    return res
  def cb_op(name, results, line, col, ast):
    if name == 'AND':
      res = [doc for doc in results[0] if doc in results[1]]
    elif name == 'OR':
      res = []
      for doc in results[0]:
        if doc not in res: res.append(doc)
      for doc in results[1]:
        if doc not in res: res.append(doc)
    elif name == 'NOT':
      res = []
      pass #TODO don't forget me here ... lying helpless in my own blood ...
    if len(res) == 0: log.info("%s no results", sqp.reformat(ast))
    else: log.info("%s %d results", sqp.reformat(ast), len(res))
    if verbose:
      for docid in res: print '   ',docid
    return res
  
  return sqp.walk_ast_depth_first(ast, cb_atom, cb_op)

def main():
  log = logging.getLogger('stderr')
  
  # get query
  if len(sys.argv) == 1: query = sys.stdin.read()
  else: query = " ".join(sys.argv[1:])
  log.info("Your query:\n%s"%query)
  
  # do search
  try:
    res = search(query, 'stderr')
  except lrparsing.ParseError:
    common.fatal("Could not parse query:\n%s\n%s"%(query, traceback.format_exc()))
  except IOError:
    common.fatal(traceback.format_exc())
  
  # print result to stdout
  log.info("\nResult: %d documents"%len(res))
  for val in res: print val

if __name__ == '__main__': main()

