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
        self.dest = None # Where the return value had to be located

    def is_done(self):
        return self.idx == len(self.stmts)

class SubScope(Scope):
    def __init__(self, stmts, line_no, scope_type):
        # create condition stmt
        new_stmt = copy.deepcopy(stmts)
        if scope_type is ScopeType.IF:
            new_stmt[0].insert(0, 'condition')
        elif scope_type is ScopeType.FOR:
            new_stmt[1].insert(0, 'condition')

            # set valid line number in increment
            new_stmt[2][-1] = new_stmt[0][-1]

        # break down single-for-loop-stmts into multiple-stmts
        sub_stmts = copy.deepcopy(new_stmt[-1])
        new_stmt.pop()
        new_stmt += sub_stmts

        super(SubScope, self).__init__(new_stmt, scope_type)
        self.line_no = copy.deepcopy(line_no)
        self.is_condition_true = True
        self.next_idx = 0
        self.declared_vars = []

    def update_idx(self):
        self.idx = self.next_idx

    def update_next_idx(self):
        if self.type is ScopeType.IF:
            if self.idx == 0:
                # 0 : ['if-condition', 'a', '3', ['number', 1.0], 3]
                self.next_idx = 1
            else:
                # 1 ~ : stmts in if scope
                self.next_idx = self.idx + 1
                if self.next_idx >= len(self.stmts):
                    self.set_done()

        elif self.type is ScopeType.FOR:
            if self.idx == 0:
                # 0 : ['assign', ['id', 'i'],['number', 0.0], 3]
                self.next_idx = 1
            elif self.idx == 1:
                # 1 : ['for-condition', 'i', '<', ['id', 'count'], 3]
                self.next_idx = 3
            elif self.idx == 2:
                # 2 : ['increment', ['id', 'i'], 3]
                self.next_idx = 1
            else:
                # 3 ~ : stmts in for loop
                self.next_idx = self.idx + 1
                if self.next_idx >= len(self.stmts):
                    self.next_idx = 2

    def set_done(self):
        self.is_condition_true = False

    def is_done(self):
        return not self.is_condition_true

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

    if isinstance(scope, SubScope):
        scope.update_next_idx()

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
            skip = 0
            if isinstance(scope, SubScope):
                if not var[1] in scope.declared_vars:
                    scope.declared_vars.append(var[1])
                    func.declare_var(var_type, var[1], lineno)
                else:
                    if scope.type is ScopeType.FOR:
                        skip = 1
                        scope.update_idx()
                        next_stmt()
                    else:
                        raise PException(f"Double declaration in if-statement!")
            else:
                func.declare_var(var_type, var[1], lineno)
        # Declaration in for-statement invoked once at first.
        LAST_LINE = lineno + skip
        scope.idx += 1
        pass

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
            if isinstance(scope, SubScope):
                if scope.type is ScopeType.FOR:
                    if lineno == scope.line_no[0]:
                        scope.update_idx()
                        next_stmt()
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
        if isinstance(scope, SubScope):
            if scope.type is ScopeType.FOR:
                if lineno == scope.line_no[0]:
                    scope.update_idx()
                    next_stmt()
        LAST_LINE = lineno
        scope.idx += 1

    elif behavior == "for":
        '''
        ['for', ['assign', ['id', 'i'],['number', 0.0], 3],
                ['i', '<', ['id', 'count'], 3],
                ['increment', ['id', 'i'], 3],
                stmts,
                [3, 5]]
        '''
        func.stack.push(SubScope(stmt[1:-1], stmt[-1],ScopeType.FOR))
        lineno = stmt[-1][0]
        LAST_LINE = lineno
        next_stmt()
    elif behavior == "if":
        '''
        ['if', ['average', '>', ['number', 40.0], 21],
               stmts,
               [21, 23]]
        '''
        func.stack.push(SubScope(stmt[1:-1], stmt[-1], ScopeType.IF))
        lineno = stmt[-1][0]
        LAST_LINE = lineno
        next_stmt()
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
    elif behavior == "condition":
        '''
        ['condition', 'a', '>', ['number', 0.0], 3]
        '''
        success, right_value = next_expr(func, stmt[3])
        if success == False:
            # TODO : need to test case that includes functcall in right expression
            pass

        left_value, condition = func.get_var(stmt[1]).value, stmt[2]
        condition = stmt[2]

        if condition == '>':
            if left_value > right_value:
                # do nothing
                pass
            else:
                scope.set_done()
        elif condition == '<':
            if left_value < right_value:
                # do nothing
                pass
            else:
                scope.set_done()
        else:
            raise PException(f"For condition({condition}) is invalid", stmt[4])

    if isinstance(scope, SubScope):
        scope.update_idx()

    while not MAIN_STACK.isEmpty():
        func = MAIN_STACK.top()
        if func.stack.isEmpty():
            MAIN_STACK.pop()
            continue

        scope = func.stack.top()
        if scope.is_done():
            if isinstance(scope, SubScope):
                for var in scope.declared_vars:
                    func.release_var(var)
            func.stack.pop()
            next_scope = func.stack.top()
            # if current scope is done, next scope must increase statement index
            if next_scope is not None:
                if isinstance(next_scope, SubScope):
                    # do nothing
                    pass
                else:
                    next_scope.idx += 1
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
    f = open("inputs/input12.c", "r")
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
