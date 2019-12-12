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
    '''func : INT ID LPAREN paramlist RPAREN lbrace stmtlist rbrace
            | FLOAT ID LPAREN paramlist RPAREN lbrace stmtlist rbrace
            | VOID ID LPAREN paramlist RPAREN lbrace stmtlist rbrace
    '''
#    p[0] = ["function", p[1], p[2], ["parameter", p[4]], [p[6]] + p[7] + [p[8]], [p.lineno(1), p[8][1]]]
    p[0] = ["function", {
                "type": p[1],
                "name": p[2],
                "params": p[4],
                "stmts": [p[6]] + p[7] + [p[8]],
                "lineno": [p.lineno(1), p[8][1]["lineno"]]
                }]
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
        p[0] = ["id", {
                    "type": p[1] + p[2],
                    "name": p[3]
                    }]
    elif len(p) == 3:
        p[0] = ["id", {
                    "type": p[1],
                    "name": p[2]
                }]
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
        p[0] = ["declare", {
                    "type": p[1] + p[2],
                    "vars": p[3],
                    "lineno": p.lineno(1)
                }]
    elif len(p) == 3:
        p[0] = ["declare", {
                    "type": p[1],
                    "vars": p[2],
                    "lineno": p.lineno(1)
                }]
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
    p[0] = ["assign", {
                "var": p[1],
                "expr": p[3],
                "lineno": p.lineno(2)
            }]
    print_log("p_assign: ", p[0])

def p_increment_id_inc(p):
    '''increment : id INCREMENT'''
    p[0] = ["increment", {
            "var": p[1],
            "lineno": p.lineno(1)
        }]
    print_log("p_increment: ", p[0])

def p_increment_inc_id(p):
    '''increment : INCREMENT id'''
    p[0] = ["increment", {
            "var": p[2],
            "lineno": p.lineno(1)
        }]
    print_log("p_increment: ", p[0])

def p_functcall(p):
    'functcall : ID LPAREN arglist RPAREN'
    func_str = p[1][-1] + '('
    func_arg_list = []
    for arg in p[3]:
        if p[3].index(arg) is not 0:
            func_str += ','
        func_str += arg[1]["str"]
        func_arg_list += arg[1]["arg_list"]
    p[0] = ["functcall", {
                "callee": p[1],
                "args": p[3],
                "arg_list": func_arg_list,
                "str": func_str,
                "lineno": p.lineno(1)
            }]
#    p[0] = ["functcall", p[1], ["args", p[3]], func_arg_list, func_str, p.lineno(1)]
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
    p[0] = ["string", {
        "arg_list": [],
        "str": p[1],
        "lineno": p.lineno(1)
    }]

def p_arg_empty(p):
    '''arg : empty'''
    p[0] = None
    print_log("p_arg: ", p[0])

def p_return(p):
    '''return : RETURN expression
              | RETURN'''
    if len(p) == 2:
        p[0] = ["return", {
                    "value": None,
                    "lineno": p.lineno(1)
            }]
    else:
        p[0] = ["return", {
                    "value": p[2],
                    "lineno": p.lineno(1)
            }]
    print_log("p_return: ", p[0])

def p_expression(p):
    '''expression : expression PLUS term
                  | expression MINUS term
                  | term
                  | casting'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        expr_arg_list = list(set(p[1][1]["arg_list"]) | set(p[3][1]["arg_list"]))
        expr_str = p[1][1]["str"] + p[2] + p[3][1]["str"]
        p[0] = ["expression", {
            "op": p[2],
            "lhs": p[1],
            "rhs": p[3],
            "arg_list": expr_arg_list,
            "str": expr_str,
            "lineno": p.lineno(1)
        }]
    print_log("p_expression: ", p[0])

def p_term(p):
    '''term : term STAR factor
            | term DIVIDE factor
            | factor'''
    if len(p) == 4:
        term_arg_list = list(set(p[1][1]["arg_list"]) | set(p[3][1]["arg_list"]))
        term_str = p[1][1]["str"] + p[2] + p[3][1]["str"]
        p[0] = ["expression", {
            "op": p[2],
            "lhs": p[1],
            "rhs": p[3],
            "arg_list": term_arg_list,
            "str": term_str,
            "lineno": p.lineno(1)
        }]
    else:
        p[0] = p[1]
    print_log("p_term: ", p[0])

def p_factor_functcall(p):
    '''factor : functcall'''
    p[0] = p[1]
    print_log("p_factor_functcall: ", p[0])

def p_factor_num(p):
    '''factor : NUMBER
              | LPAREN NUMBER RPAREN
              | LPAREN PLUS NUMBER RPAREN
              | LPAREN MINUS NUMBER RPAREN'''
    if len(p) == 2:
        p[0] = ["number", {
            "value": p[1],
            "arg_list": [],
            "str": str(p[1]),
            "lineno": p.lineno(1)
        }]
    elif len(p) == 4:
        p[0] = ["number", {
            "value": p[2],
            "arg_list": [],
            "str": str(p[2]),
            "lineno": p.lineno(1)
        }]
    else:
        if (p[2] == '+'):
            num = p[3]
        elif (p[2] == '-'):
            num = -p[3]

        p[0] = ["number", {
            "value": num,
            "arg_list": [],
            "str": str(num),
            "lineno": p.lineno(1)
        }]

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
        p[0] = ["id", {
            "name": p[1],
            "arg_list": [p[1]],
            "str": p[1],
            "lineno": p.lineno(1)
        }]
    else:
        array_arg_list = list(set([p[1]]) | set(p[3][1]["arg_list"]))
        array_str = p[1] + '[' + p[3][1]["str"] + ']'
        p[0] = ["array", {
            "name": p[1],
            "index": p[3],
            "arg_list": array_arg_list,
            "str": array_str,
            "lineno": p.lineno(1)
        }]
    print_log("p_factor: ", p[0])

def p_casting(p):
    '''casting : LPAREN INT RPAREN expression
               | LPAREN FLOAT RPAREN expression'''
    casting_str = '(' + p[2] + ')' + p[4][1]["str"]

    p[0] = ["casting", {
        "type": p[2],
        "expr": p[4],
        "arg_list": p[4][1]["arg_list"],
        "str": casting_str,
        "lineno": p.lineno(1)
    }]
    print_log("p_casting: ", p[0])

def p_forloop(p):
    'forloop : FOR LPAREN assign SEMICOLON condition SEMICOLON increment RPAREN lbrace stmtlist rbrace'
    p[0] = ["for", {
        "assign": p[3],
        "condition": p[5],
        "increment": p[7],
        "stmts": [p[9]] + p[10] + [p[11]],
        "lineno": [p.lineno(1), p[11][1]],
    }]
    print_log("p_forloop: ", p[0])

def p_if(p):
    'if : IF LPAREN condition RPAREN lbrace stmtlist rbrace'
    p[0] = ["if", {
        "condition": p[3],
        "stmts": [p[5]] + p[6] + [p[7]],
        "lineno": [p.lineno(1), p[7][1]]
    }]
    print_log("p_if: ", p[0])

def p_condition(p):
    'condition : ID cmp expression'
    p[0] = ["condition", {
        "var": p[1],
        "cmp": p[2],
        "expr": p[3],
        "lineno": p.lineno(1)
    }]
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

def p_lbrace(p):
    'lbrace : LBRACE'
    p[0] = ["{", {"lineno": p.lineno(1)}]

def p_rbrace(p):
    'rbrace : RBRACE'
    p[0] = ["}", {"lineno": p.lineno(1)}]


def p_error(p):
    while True:
      tok = parser.token() # get the next token
      print("token type: ", tok.type)
      if not tok or tok.type == 'SEMICOLON': break
    
    parser.errok()
    print("Syntax error : line", p.lineno)
    return tok
    # exit()

def get_parser_tree(code):
    global parser
    clexer = CLexer()
    lexer = clexer.build()
    tokens = clexer.tokens
    parser = yacc.yacc()
    return parser.parse(code, lexer=lexer)

parser = None

if __name__ == '__main__':
    f = open("inputs/easy.c")
    code = "".join(f.readlines())
    f.close()

    print(get_parser_tree(code))
