import ply.yacc as yacc

def p_code(p):
    'code : funclist'
    pass

def p_funclist(p):
    '''funclist : funclist func
                | func'''
    pass

def p_func(p):
    '''func : INT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | FLOAT ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
            | VOID ID LPAREN paramlist RPAREN LBRACE stmtlist RBRACE
    '''
    pass

def p_paramlist(p):
    '''paramlist : param COMMA paramlist
                 | param'''
    pass

def p_param(p):
    '''param : VOID
             | empty
             | INT ID
         	 | FLOAT ID
        	 | INT STAR ID
        	 | FLOAT STAR ID'''
    pass

def p_empty(p):
    'empty :'
    pass

def p_stmtlist(p):
    '''stmtlist : stmt stmtlist
                | stmt'''
    pass

def p_stmt(p):
    '''stmt : declare semicolonlist
            | assign semicolonlist
            | increment semicolonlist
            | functcall semicolonlist
            | return semicolonlist
            | forloop
            | if'''
    pass

def p_semicolonlist(p):
    '''semicolonlist : SEMICOLON semicolonlist
                     | SEMICOLON'''
    pass

def p_declare(p):
    '''declare : INT ID
               | INT STAR ID
               | FLOAT ID
               | FLOAT STAR ID'''
    pass

def p_assign(p):
    'assign : ID ASSIGN expression'
    pass

def p_increment(p):
    '''increment : ID INCREMENT
                 | INCREMENT ID'''
    pass

def p_functcall(p):
    'functcall : ID LPAREN arglist RPAREN'
    pass

def p_arglist(p):
    '''arglist : arg COMMA arglist
               | arg'''
        pass

def p_arg(p):
    'arg : ID | empty'
    pass

def p_return(p):
    '''return : RETURN expression
              | RETURN'''
    pass

def p_expression(p):
    '''expression : term PLUS expression
                  | term MINUS expression
                  | term
                  | LPAREN expression RPAREN'''
    pass

def p_term(p):
    '''term : factor STAR term
            | factor DIVIDE term
            | factor'''
    pass

def p_factor(p):
    'factor : NUMBER | ID'
    pass

def p_casting(p):
    '''casting : LPAREN INT RPAREN expression
               | LPAREN FLOAT RPAREN expression'''
    pass

def p_forloop(p):
    'forloop : FOR LPAREN assign SEMICOLON condition SEMICOLON increment RPAREN LBRACE stmtlist RBRACE'
    pass

def p_if(p):
    'if : IF LPAREN RPAREN LBRACE stmtlist RBRACE'
    pass

def p_condition(p):
    'condition : ID cmp expression'
    pass

def p_cmp(p):
    'cmp : GT | GTE | LT | LTE | EQ | NEQ'
    pass
