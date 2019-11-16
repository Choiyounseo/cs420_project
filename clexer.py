import ply.lex as lex

reserved = {
    'void' : 'VOID',
    'return': 'RETURN',
    'for': 'FOR',
    'if': 'IF',
    'int': 'INT',
    'float': 'FLOAT',
}

tokens = [
  "ID",
  "NUMBER",
  "ASSIGN",
  "PLUS",
  "MINUS",
  "STAR",
  "DIVIDE",
  "INCREMENT",
  "GT",
  "GTE",
  "LT",
  "LTE",
  "EQ",
  "NEQ",
  "SEMICOLON",
  "COMMA",
  "LPAREN",
  "RPAREN",
  "LBRACE",
  "RBRACE",
  "LBRACKET",
  "RBRACKET"
] + list(reserved.values())

class CLexer:
  def __init__(self):
    self.tokens = tokens
    self.reserved = reserved
    self.lexer = None

  def t_ID(self, t):
    r'([a-zA-Z_][0-9a-zA-Z_]*)'
    t.type = self.reserved.get(t.value, 'ID')
    return t
  
  t_ASSIGN = r'='
  t_PLUS = r'\+'
  t_MINUS = r'\-'
  t_STAR = r'\*'
  t_DIVIDE = r'/'
  t_INCREMENT = r'\+\+'
  t_GT = r'>'
  t_GTE = r'>='
  t_LT = r'<'
  t_LTE = r'<='
  t_EQ = r'=='
  t_NEQ = r'!='
  t_SEMICOLON = r';'
  t_LPAREN = r'\('
  t_RPAREN = r'\)'
  t_LBRACE = r'\{'
  t_RBRACE = r'\}'
  t_LBRACKET = r'\['
  t_RBRACKET = r'\]'
  t_ignore = ' \t'
  t_VOID = r'void'
  t_RETURN = r'return'
  t_FOR = r'for'
  t_IF = r'if'
  t_INT = r'int'
  t_FLOAT = r'float'
  
  def t_NUMBER(self, t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print("Integer value too large %d", t.value)
        t.value = 0
    return t
  
  def t_newline(self, t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    
  def t_error(self, t):
    prinnt("Illigal character '%s'" % t.value[0])
    t.lexer.skip(1)

  def build(self, **kwargs):
    self.lexer = lex.lex(object=self, **kwargs)
    return self.lexer