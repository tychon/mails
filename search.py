#!/usr/bin/python
import sys, logging, traceback
import requests, json

import common
import config, lrparsing
import searchqueryparser as sqp

# Returns a list of document ids matching the search criteria.
# Raises lrparsing.ParseException on malformed query.
# May return an empty list, but not None.
def search(query, logger='none', verbose=False):
  log = logging.getLogger(logger)
  
  ast = sqp.parse(query) # ParseException handled by caller
  log.info("Abstract Syntax Tree:\n%s\n"%sqp.formatTree(ast))
  
  def cb_atom(name, tok, line, col):
    tok = tok.lower()
    if name == 'VIEW':
      _, res = common.get_view(tok, "line %d col %d: Could not GET view."%(line, col), logger)
      res = common.uniquify(res)
    else:
      _, res = common.get_view('%s?startkey="%s"&endkey="%s\u9999"'
                     %(name.lower(), tok, tok)
                   , "line %d col %d: Could not GET view."%(line, col), logger)
    if verbose:
      for row in res: print '   ',row
    if len(res) == 0: log.info("%s %s (no results)", name, tok)
    else: log.info("%s %s (%d results)", name, tok, len(res))
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
      # retrieve all documents of type mail
      _, res = common.get_view('all_mails', "line %d col %d: Could not GET view."%(line, col), logger)
      # do NOT conjunction
      res = [doc for doc in res if doc not in results[0]]
    
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

