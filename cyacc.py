import ply.yacc as yacc
from clexer import CLexer

DEBUG = False

def print_log(name, p):
    if DEBUG:
        print(name, p)

def p_code(p):
    'code : funclist'
    p[0] = p[1]

def p_funclist(p):
    '''funclist : funclist func
                | func'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]
    print_log("p_funclist: ", p[0])

# ignore function inside function ..
def p_func(p):
    '''func : INT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | FLOAT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | VOID ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
    '''
    p[0] = ["function", p[1], p[2], ["parameter", p[4]], p[7], [p.lineno(1), p.lineno(8)]]
    print_log("p_func: ", p[0])

def p_paramlist(p):
    '''paramlist : paramlist COMMA param
                 | param'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]
    print_log("p_paramlist: ", p[0])

def p_param(p):
    '''param : VOID
             | empty
             | INT ID
         	 | FLOAT ID
        	 | INT STAR ID
        	 | FLOAT STAR ID'''
    if len(p) == 4:
        p[0] = ["id", p[1] + p[2], p[3]]
    elif len(p) == 3:
        p[0] = ["id", p[1], p[2]]
    elif len(p) == 2:
        p[0] = p[1]
    else:
        p_error(p)
    print_log("p_param: ", p[0])

def p_empty(p):
    'empty :'
    p[0] = None

def p_stmtlist(p):
    '''stmtlist : stmtlist stmt
                | stmt'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]
    print_log("p_stmtlist: ", p[0])

def p_stmt(p):
    '''stmt : declare semicolonlist
            | assign semicolonlist
            | increment semicolonlist
            | functcall semicolonlist
            | return semicolonlist
            | forloop
            | if'''
    p[0] = p[1]
    print_log("p_stmt: ", p[0])

def p_semicolonlist(p):
    '''semicolonlist : SEMICOLON semicolonlist
                     | SEMICOLON'''
    pass

def p_declare(p):
    '''declare : INT declarelist
               | FLOAT declarelist
               | INT STAR declarelist
               | FLOAT STAR declarelist'''
    if len(p) == 4:
        p[0] = ["declare", p[1] + p[2], p[3], p.lineno(1)]
    elif len(p) == 3:
        p[0] = ["declare", p[1], p[2], p.lineno(1)]
    print_log("p_declare: ", p[0])

def p_declarelist(p):
    '''declarelist : declarelist COMMA id
                   | id'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_assign(p):
    'assign : id ASSIGN expression'
    p[0] = ["assign", p[1], p[3], p.lineno(2)]
    print_log("p_assign: ", p[0])

def p_increment_id_inc(p):
    '''increment : id INCREMENT'''
    p[0] = ["increment", p[1], p.lineno(1)]
    print_log("p_increment: ", p[0])

def p_increment_inc_id(p):
    '''increment : INCREMENT id'''
    p[0] = ["increment", p[2], p.lineno(1)]
    print_log("p_increment: ", p[0])

def p_functcall(p):
    'functcall : ID LPAREN arglist RPAREN'
    func_str = p[1][-1] + '('
    for arg in p[3]:
        if p[3].index(arg) is not 0:
            func_str += ','
        func_str += arg[-1]
    p[0] = ["functcall", p[1], ["args", p[3]], p.lineno(1), func_str]
    print_log("p_functcall: ", p[0])

def p_arglist(p):
    '''arglist : arglist COMMA arg
               | arg'''
    arg = None
    if len(p) == 4:
        p[0] = p[1]
        arg = p[3]
    else:
        p[0] = []
        arg = p[1]

    if arg is not None:
        p[0].append(arg)
    print_log("p_arglist: ", p[0])

def p_arg(p):
    '''arg : expression'''
    p[0] = p[1]
    print_log("p_arg: ", p[0])

def p_arg_string(p):
    '''arg : string'''
    p[0] = p[1]
    print_log("p_arg: ", p[0])

def p_string(p):
    '''string : STRING'''
    p[0] = ["string", p[1]]

def p_arg_empty(p):
    '''arg : empty'''
    p[0] = None
    print_log("p_arg: ", p[0], "")

def p_return(p):
    '''return : RETURN expression
              | RETURN'''
    if len(p) == 2:
        p[0] = ["return", None, p.lineno(1)]
    else:
        p[0] = ["return", p[2], p.lineno(1)]
    print_log("p_return: ", p[0])

def p_expression(p):
    '''expression : term PLUS expression
                  | term MINUS expression
                  | functcall
                  | term
                  | casting'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        expr_str = p[1][-1] + p[2] + p[3][-1]
        p[0] = [p[2], p[1], p[3], expr_str]
    print_log("p_expression: ", p[0])

def p_term(p):
    '''term : factor STAR term
            | factor DIVIDE term
            | factor'''
    if len(p) == 4:
        term_str = p[1][-1] + p[2] + p[3][-1]
        p[0] = [p[2], p[1], p[3], term_str]
    else:
        p[0] = p[1]
    print_log("p_term: ", p[0])

def p_factor_num(p):
    '''factor : NUMBER
              | LPAREN NUMBER RPAREN
              | LPAREN PLUS NUMBER RPAREN
              | LPAREN MINUS NUMBER RPAREN'''
    if len(p) == 2:
      p[0] = ["number", p[1], str(p[1])]
    elif len(p) == 4:
      p[0] = ["number", p[2], str(p[2])]
    else:
      if (p[2] == '+'):
        num = p[3]
      elif (p[2] == '-'):
        num = -p[3]
      p[0] = ["number", num, str(num)]

    print_log("p_factor: ", p[0])

def p_factor_paren(p):
    '''factor : LPAREN expression RPAREN'''
    p[0] = p[2]
    print_log("parentheses_factor: ", p[0])

def p_factor_id(p):
    '''factor : id'''
    p[0] = p[1]
    print_log("p_factor: ", p[0])

def p_id(p):
    '''id : ID
          | ID LBRACKET expression RBRACKET'''
    if len(p) == 2:
        p[0] = ["id", p[1]]
    else:
        array_str = p[1][-1] + '[' + p[3][-1] + ']'
        p[0] = ["array", p[1], p[3], array_str]
    print_log("p_factor: ", p[0])

def p_casting(p):
    '''casting : LPAREN INT RPAREN expression
               | LPAREN FLOAT RPAREN expression'''
    casting_str = '(' + p[2] + ')'+p[4][-1]
    p[0] = ["casting", p[2], p[4], casting_str]
    print_log("p_casting: ", p[0])

def p_forloop(p):
    'forloop : FOR LPAREN assign SEMICOLON condition SEMICOLON increment RPAREN LBRACE stmtlist RBRACE'
    p[0] = ["for", p[3], p[5], p[7], p[10], [p.lineno(1), p.lineno(11)]]
    print_log("p_forloop: ", p[0])

def p_if(p):
    'if : IF LPAREN condition RPAREN LBRACE stmtlist RBRACE'
    p[0] = ["if", p[3], p[6], [p.lineno(1), p.lineno(7)]]
    print_log("p_if: ", p[0])

def p_condition(p):
    'condition : ID cmp expression'
    p[0] = [p[1], p[2], p[3], p.lineno(1)]
    print_log("p_condition: ", p[0])

def p_cmp(p):
    '''cmp : GT
           | GTE
           | LT
           | LTE
           | EQ
           | NEQ'''
    p[0] = p[1]
    print_log("p_cmp: ", p[0])

def p_error(p):
    while True:
      tok = parser.token() # get the next token
      print("token type: ", tok.type)
      if not tok or tok.type == 'SEMICOLON': break
    
    parser.errok()
    print("Syntax error : line", p.lineno)
    return tok
    # exit()

clexer = CLexer()
lexer = clexer.build()
tokens = clexer.tokens
parser = yacc.yacc()