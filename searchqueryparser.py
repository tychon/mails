
import lrparsing
from lrparsing import Keyword, Ref, Token

class QueryParser(lrparsing.Grammar):
  atom = Token(re="FROM|TO|DATE|LABEL|VIEW|SINCE|BEFORE") + Token(re="[^\s()]+")
  op = Ref('op')
  op = '(' + Keyword('AND', case=False) + op + op + ')' \
      | '(' + Keyword('OR', case=False) + op + op + ')' \
      | '(' + Keyword('NOT', case=False) + op + ')' \
      | atom
  START = op

# Walk the generated ast.
# Calls cb_atom(FROM|TO|SINCE|BEFORE|LABEL, sometext)
# Calls cb_op(AND|OR|NOT, [results from operands])
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
    if cb_op.func_code.co_argcount == 2: return cb_op(opname, results)
    else: return cb_op(opname, results, ast[2][3], ast[2][4], ast)
  elif name == 'atom':
    atomname = ast[1][1]
    atomtok = ast[2][1]
    if cb_atom.func_code.co_argcount == 2: return cb_atom(atomname, atomtok)
    else: return cb_atom(atomname, atomtok, ast[1][3], ast[1][4])

# Get the formatted query back.
def reformat(ast):
  def cb_atom(name, tok): return name + ' ' + tok
  def cb_op(name, operands): return '(' + name + ' ' + ' '.join(operands) + ')'
  return walk_ast_depth_first(ast, cb_atom, cb_op)

# Format query with many whitespaces in a tree.
# Makes data tokens .lower()
def formatTree(ast):
  def cb_atom(name, tok):
    return name+' '+tok.lower()
  def cb_op(name, operands):
    return ('('+name+'\n'
        +'\n'.join(['  '+op.replace('\n', '\n  ') for op in operands])+')')
  return walk_ast_depth_first(ast, cb_atom, cb_op)

def parse(input): return QueryParser.parse(input)

