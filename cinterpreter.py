from cyacc import lexer, parser
from os import listdir, path
import copy
import enum

class PException(Exception):
    def __init__(self, msg, lineno=None):
        if lineno is None:
            Exception.__init__(self, msg)
        else:
            Exception.__init__(self, f"[Line {lineno}] {msg}")

class Stack:
    def __init__(self):
        self.stack = []

    def push(self, elem):
        self.stack.append(elem)

    def top(self):
        if len(self.stack) == 0:
            return None

        return self.stack[-1]

    def pop(self):
        if len(self.stack) != 0:
            self.stack.pop()

    def isEmpty(self):
        return len(self.stack) == 0


MAIN_STACK = Stack()
PLAIN_CODE = ""
LAST_LINE = 0


class Return:
    def __init__(self, value):
        self.value = value

class VAR:
    def __init__(self, var_type, lineno):
        self.type = var_type
        self.value = None
        self.history = [[lineno, None]]

    def assign(self, value, lineno):
        if "int" in self.type:
            value = int(value)
        if "float" in self.type:
            value = float(value)

        self.history.append([lineno, value])
        self.value = value

class ScopeType(enum.Enum):
    FUNC = 0
    IF = 1
    FOR = 2

class Scope:
    def __init__(self, stmts, type):
        self.stmts = copy.deepcopy(stmts)
        self.type = type
        self.idx = 0
        self.declared_vars = []
        self.dest = None # Where the return value had to be located

class Function:
    def __init__(self):
        self.vars = {}
        self.stack = Stack()

    def __init__(self, func, args=[]):
        self.vars = {}
        self.stack = Stack()

        name = func[2]
        # Argument
        params = func[3][1]
        expected_args_length = 0
        if len(params) != 0 and params != ["void"]:
            expected_args_length = len(params)
            if "void" in params:
                raise PException(f"Function {name}'void' must be the first and only parameter if specified")

        if expected_args_length != len(args):
            raise PException(f"Function {name}, expected {expected_args_length} arguments, but {len(args)} given")

        for param, arg in zip(params, args):
            if "int" in param[1]:
                self.vars[param[2]] = int(arg)
            elif "float" in param[1]:
                self.vars[param[2]] = float(arg)

        # Func Scope
        self.stack.push(Scope(func[4], ScopeType.FUNC))

    def declare_var(self, var_type, var_name, lineno):
        var = VAR(var_type, lineno)
        if not var_name in self.vars:
            self.vars[var_name] = []
        self.vars[var_name].append(var)

    def get_var(self, id):
        if not id in self.vars:
            return None

        return self.vars[id][-1]

    def release_var(self, var_name):
        self.vars[var_name].pop()
        if len(self.vars[var_name]) == 0:
            self.vars.pop(var_name, None)

# return finished, value.
# If there's another functcall in expr, it return False, None
# Otherwise return True, value
def next_expr(func, expr):
    global LAST_LINE

    behavior = expr[0]
    if behavior == 'number':
        return True, expr[1]
    elif behavior == 'id':
        var = func.get_var(expr[1])
        if var == None:
            raise PException(f"Varaible {expr[1]} not found")
        return True, var.value
    elif behavior == 'functcall':
        func.dest = []
        # TODO: Push to the stack for functcall
        expr = func.dest
        return None, False
    elif behavior == 'casting':
        finished, value = next_expr(func, expr[2])
        if not finished:
            return False, None
        if expr[1] == 'int':
            return True, int(value)
        elif expr[1] == 'float':
            return True, float(value)
        raise PException(f"Invalid casting {expr[1]}")
    else:
        finished, value1 = next_expr(func, expr[1])
        if not finished:
            return False, None
        finished, value2 = next_expr(func, expr[2])
        if not finished:
            return False, None

        value = None
        if expr[0] == '+':
            value = value1 + value2
        elif expr[0] == '-':
            value = value1 - value2
        elif expr[0] == '/':
            if value2 == 0:
                raise PException("Division by zero")
            value = value1 / value2
        elif expr[0] == '*':
            value = value1 * value2
        else:
            raise PException(f"Invalid operator {expr[0]}")
        return True, value

def next_stmt():
    global LAST_LINE

    func = MAIN_STACK.top()
    if func is None:
        return

    scope = func.stack.top()
    stmt = scope.stmts[scope.idx]
#    print(stmt)

    behavior = stmt[0]
    if behavior == "declare":
        '''
        ['declare', 'int', [
                ['id', 'i'],
                ['id', 'total']
            ], 2]
        '''
        var_type, var_list, lineno = stmt[1:]
        for var in var_list:
            scope.declared_vars.append(var[1])
            func.declare_var(var_type, var[1], lineno)

        LAST_LINE = lineno
        scope.idx += 1

    elif behavior == "assign":
        '''
        ['assign', ['id', 'count'], expr, 0]
        '''
        var_info, expr, lineno = stmt[1:]
        var = func.get_var(var_info[1])
        if var == None:
            raise PException(f"Varaible {var_info[1]} not found")
        finished, value = next_expr(func, expr)
        if finished:
            var.assign(value, lineno)
            LAST_LINE = lineno
            scope.idx += 1

    elif behavior == "increment":
        '''
        ['increment', ['id', 'i'], 0]
        '''
        var_info, lineno = stmt[1:]
        var = func.get_var(var_info[1])
        if var == None:
            raise PException(f"Varaible {var_info[1]} not found")
        value = var.value
        var.assign(value + 1, lineno)
        LAST_LINE = lineno
        scope.idx += 1

    elif behavior == "for":
        '''
        ['for', ['assign', ['id', 'i'],['number', 0.0], 0],
                ['i', '<', ['id', 'count'], 17],
                ['increment', ['id', 'i'], 0],
                stmts,
                [21, 23]]
        '''
        pass
    elif behavior == "if":
        '''
        ['if', ['average', '>', ['number', 40.0], 21],
               stmts,
               [21, 23]]
        '''
        pass
    elif behavior == "functcall":
        '''
        ['functcall', 'printf',
                        ['args', [['string', '"%f\\n"'], ['id', 'average']]],
                        22]
        '''
        callee, args_info, lineno = stmt[1:]
        if callee == "printf":
            args_info = args_info[1]
            printf_format = args_info[0][1]
            args = []
            for arg in args_info[1:]:
                if arg[0] == 'id':
                    var = func.get_var(arg[1])
                    if var == None:
                        raise PException(f"Varaible {var_info[1]} not found")
                    args.append(var.value)
                elif arg[0] == 'number':
                    args.append(arg[1])

            print(printf_format % tuple(args))
            LAST_LINE = lineno
            scope.idx += 1
        pass
    elif behavior == "return":
        '''
        ['return', ['/', ['id', 'total'], ['id', 'count']], 6]
        '''
        pass

    while not MAIN_STACK.isEmpty():
        func = MAIN_STACK.top()
        if func.stack.isEmpty():
            MAIN_STACK.pop()
            continue

        scope = func.stack.top()
        if scope.idx == len(scope.stmts):
            func.stack.pop()
            continue
        break

def interpret(tree):
    # Function index
    func = {}
    for func_info in tree:
        func[func_info[2]] = func_info

    if not "main" in func:
        raise PException("Main function doesn't exist")

    MAIN_STACK.push(Function(func["main"]))

    while not MAIN_STACK.isEmpty():
        cmd = ""
        while True:
            cmd = input("Input Command(next [number] / print [variable] / trace [variable]): ").strip().split(" ")
            if len(cmd) != 2: continue
            if not cmd[0] in ["next", "print", "trace"]: continue
            if cmd[0] == "next" and not cmd[1].isdigit(): continue
            break

        if cmd[0] == "next":
            cnt = int(cmd[1])
            while cnt > 0:
                next_stmt()
                cnt -= 1

        elif cmd[0] == "print":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var == None:
                print(f"Variable {cmd[1]} not found")
            else:
                print(f"Value of {cmd[1]}: {var.value}")

        elif cmd[0] == "trace":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var == None:
                print(f"Variable {cmd[1]} not found")
            else:
                print(f"History of {cmd[1]}")
                for history in var.history:
                    print(f"Line {history[0]}: {history[1]}")

        print(f"Current stmt: (Line {LAST_LINE}) {PLAIN_CODE[LAST_LINE]}")

def process():
    global PLAIN_CODE
    f = open("inputs/input0.c", "r")
    PLAIN_CODE = f.readlines()
    code = "".join(PLAIN_CODE)
    PLAIN_CODE = [""] + PLAIN_CODE # PLAIN_CODE[1] indicates Line 1
    f.close()

    tree = parser.parse(code, lexer=lexer)
#    print(tree)
    interpret(tree)

if __name__ == "__main__":
    try:
        process()
    except PException as e:
        print("Compile Error: ", e)