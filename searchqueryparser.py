
import lrparsing
from lrparsing import Keyword, Ref, Token

class QueryParser(lrparsing.Grammar):
  atom = Token(re="FROM|TO|SINCE|BEFORE|LABEL") + Token(re="[^ ()]+|\"[^\"]*\"")
  op = Ref('op')
  op = '(' + Keyword('AND', case=False) + op + op + ')' \
      | '(' + Keyword('OR', case=False) + op + op + ')' \
      | '(' + Keyword('NOT', case=False) + op + ')' \
      | atom
  START = op

# Walk the generated ast.
def walk_ast_depth_first(ast, cb_atom, cb_op):
  name = ast[0].name
  if name == 'START': return walk_ast_depth_first(ast[1], cb_atom, cb_op)
  elif name == 'op':
    if len(ast) == 2:
      return walk_ast_depth_first(ast[1], cb_atom, cb_op)
    opname = ast[2][1]
    if opname == 'NOT': results = [walk_ast_depth_first(ast[3], cb_atom, cb_op)]
    else: results= [walk_ast_depth_first(ast[3], cb_atom, cb_op)
                  , walk_ast_depth_first(ast[4], cb_atom, cb_op)]
    return cb_op(opname, results)
  elif name == 'atom':
    atomname = ast[1][1]
    atomtok = ast[2][1]
    return cb_atom(atomname, atomtok)

# Get the formatted query back.
def reformat(ast):
  def cb_atom(name, tok): return name + ' ' + tok
  def cb_op(name, operands): return '(' + name + ' ' + ' '.join(operands) + ')'
  return walk_ast_depth_first(ast, cb_atom, cb_op)

# Format query with many whitespaces in a tree.
def formatTree(ast):
  def cb_atom(name, tok):
    return name+' '+tok
  def cb_op(name, operands):
    return ('('+name+'\n'
        +'\n'.join(['  '+op.replace('\n', '\n  ') for op in operands])+')')
  return walk_ast_depth_first(ast, cb_atom, cb_op)

def parse(input): return QueryParser.parse(input)

