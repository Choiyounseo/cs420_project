import ply.yacc as yacc
from clexer import CLexer

def p_code(p):
    'code : funclist'
    p[0] = p[1]
    print("p_code: ", p[0])

def p_funclist(p):
    '''funclist : funclist func
                | func'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]
    print("p_funclist: ", p)

def p_func(p):
    '''func : INT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | FLOAT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | VOID ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
    '''
    p[0] = ["function", p[1], p[2], ["parameter", p[4]], p[7], [p.lineno(1), p.lineno(8)]]
    print("p_func: ", p)

def p_paramlist(p):
    '''paramlist : param COMMA paramlist
                 | param'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]
    print("p_paramlist: ", p)

def p_param(p):
    '''param : VOID
             | empty
             | INT ID
         	 | FLOAT ID
        	 | INT STAR ID
        	 | FLOAT STAR ID'''
    if len(p) == 4:
        p[0] = ["id", p[1]+p[2], p[3]]
    elif len(p) == 3:
        p[0] = ["id", p[1], p[2]]
    elif len(p) == 2:
        p[0] = p[1]
    else:
        p_error(p)
    print("p_param: ", p)

def p_empty(p):
    'empty :'
    p[0] = None
    print("p_empty: ", p[0])

def p_stmtlist(p):
    '''stmtlist : stmt stmtlist
                | stmt'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]
    print("p_stmtlist: ", p)

def p_stmt(p):
    '''stmt : declare semicolonlist
            | assign semicolonlist
            | increment semicolonlist
            | functcall semicolonlist
            | return semicolonlist
            | forloop
            | if'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]
    print("p_stmt: ", p)

def p_semicolonlist(p):
    '''semicolonlist : SEMICOLON semicolonlist
                     | SEMICOLON'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = [p[1]]
    print("p_semicolonlist: ", p[0])

def p_declare(p):
    '''declare : INT ID
               | INT STAR ID
               | FLOAT ID
               | FLOAT STAR ID'''
    print("p_declare: ", p)
    pass

def p_assign(p):
    'assign : ID ASSIGN expression'
    print("p_assign: ", p)
    pass

def p_increment(p):
    '''increment : ID INCREMENT
                 | INCREMENT ID'''
    print("p_increment: ", p)
    pass

def p_functcall(p):
    'functcall : ID LPAREN arglist RPAREN'
    print("p_functcall: ", p)
    pass

def p_arglist(p):
    '''arglist : arg COMMA arglist
               | arg'''
    print("p_arglist: ", p)
    pass

def p_arg(p):
    '''arg : ID
           | empty'''
    print("p_arg: ", p)
    pass

def p_return(p):
    '''return : RETURN expression
              | RETURN'''
    if len(p) == 2:
        p[0] = ["return", None, p.lineno(1)]
    else:
        p[0] = ["return", p[2], p.lineno(1)]
    print("p_return: ", p)

def p_expression(p):
    '''expression : term PLUS expression
                  | term MINUS expression
                  | term
                  | LPAREN expression RPAREN
                  | casting'''
    print("p_expression: ", p)
    pass

def p_term(p):
    '''term : factor STAR term
            | factor DIVIDE term
            | factor'''
    print("p_term: ", p)
    pass

def p_factor(p):
    '''factor : NUMBER
              | ID
              | ID LBRACKET expression RBRACKET'''
    print("p_factor: ", p) 
    pass

def p_casting(p):
    '''casting : LPAREN INT RPAREN expression
               | LPAREN FLOAT RPAREN expression'''
    print("p_casting: ", p)
    pass

def p_forloop(p):
    'forloop : FOR LPAREN assign SEMICOLON condition SEMICOLON increment RPAREN LBRACE stmtlist RBRACE'
    print("p_forloop: ", p)
    pass

def p_if(p):
    'if : IF LPAREN RPAREN LBRACE stmtlist RBRACE'
    print("p_if: ", p)
    pass

def p_condition(p):
    'condition : ID cmp expression'
    print("p_condition: ", p)
    pass

def p_cmp(p):
    '''cmp : GT
           | GTE
           | LT
           | LTE
           | EQ
           | NEQ'''
    print("p_cmp: ", p)
    pass

def p_error(p):
    print(p)
    print("Syntax error : line", p.lineno)
    exit()

clexer = CLexer()
lexer = clexer.build()
tokens = clexer.tokens
parser = yacc.yacc()