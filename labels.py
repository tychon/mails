# usage:
#   l = Labeller(path='~/rules')
#   l.check(metadata)

import os, sys, re
import common, logging

import lrparsing
from lrparsing import Keyword, List, Ref, Token

class RuleParser(lrparsing.Grammar):
  key = Keyword('FROM') | Keyword('TO') | Keyword('DATE') | Keyword('LABEL')
  #rule = Token(re="FROM|TO|SINCE|BEFORE|LABEL", case=False) + ':' + Token(re="/.+/")
  rule = key + ':' + Token(re="/[^\n]+/")
  section = '[' + Token(re="\\w+") + ']' + '\n' + List(rule, '\n') + '\n'
  START = List(section, '\n')

class Labeller:
  def __init__(self, path=None, string=None):
    self.sections = []
    if path: ast = RuleParser.parse(open(os.path.expanduser(path)).read())
    elif string: ast = RuleParser.parse(string)
    def cb_section(secname, rules): self.sections.append({'name':secname, 'rules':rules})
    def cb_rule(kw, regex): return {'key':kw, 'regex':regex}
    self._walk_ast(ast, cb_section, cb_rule)
    self._create_regexes()
  
  def _walk_ast(self, ast, cb_section, cb_rule):
    name = ast[0].name
    if name == 'START':
      return [self._walk_ast(ast[i], cb_section, cb_rule) for i in range(1, len(ast), 2)]
    elif name == 'section':
      secname = ast[2][1].lower()
      rules = [self._walk_ast(ast[i], cb_section, cb_rule) for i in range(5, len(ast), 2)]
      return cb_section(secname, rules)
    elif name == 'rule':
      key = ast[1][1][1].lower()
      regex = ast[3][1]
      return cb_rule(key, regex)
  
  def _create_regexes(self):
    for section in self.sections:
      for rule in section['rules']:
        rule['regex'] = re.compile(rule['regex'][1:-1])
  
  def _match(self, key, regex, metadata):
    if key == 'from' or key == 'to' or key == 'labels':
      addrs = metadata.get(key, None)
      if not addrs: return False
      for addr in addrs:
        if regex.match(addr): return True
      return False
    elif key == 'date':
      date = metadata.get('date', None)
      if not date: return False
      if regex.match(date): return True
      else: return False
  
  # Adds labels to metadata['labels']
  def check(self, metadata):
    labels = metadata.get('labels', [])
    for section in self.sections:
      allrulesmatched = True
      for rule in section['rules']:
        if not self._match(rule['key'], rule['regex'], metadata):
          allrulesmatched = False
          break
      if allrulesmatched: labels.append(section['name'])
    metadata['labels'] = common.uniquify(labels)

