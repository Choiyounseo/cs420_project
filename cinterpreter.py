from cyacc import get_parser_tree
from coptimization import *
import copy
import enum
import sys


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
PLAIN_CODE_ONE_LINE = ""
CURRENT_LINE = 0
FUNCTION_DICT = {}


class Return:
    def __init__(self, value):
        self.value = value


class VAR:
    def __init__(self, var_type, lineno, value=None):
        self.type = var_type
        self.value = value
        self.history = [[lineno, value]]

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
        self.dest = [] # Where the return value had to be located

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
        self.assigned_vars = []

    def update_idx(self):
        self.idx = self.next_idx

    def update_next_idx(self):
        if self.type is ScopeType.IF:
            if self.idx == 0:
                # 0 : ['condition', 'a', '3', ['number', 0, '0'], 3]
                self.next_idx = 1
            else:
                # 1 ~ : stmts in if scope
                self.next_idx = self.idx + 1
                if self.next_idx >= len(self.stmts):
                    self.set_done()

        elif self.type is ScopeType.FOR:
            if self.idx == 0:
                # 0 : ['assign', ['id', 'i'],['number', 0, '0'], 3]
                self.next_idx = 1
            elif self.idx == 1:
                # 1 : ['condition', 'i', '<', ['id', 'count'], 3]
                self.next_idx = 3
            elif self.idx == 2:
                # 2 : ['increment', ['id', 'i'], 3]
                self.next_idx = 1
            else:
                # 3 ~ : stmts in for loop
                self.next_idx = self.idx + 1

    def set_done(self):
        self.is_condition_true = False

    def is_done(self):
        return not self.is_condition_true


class Function(Optimization):
    def __init__(self):
        super(Function, self).__init__()
        self.vars = {}
        self.stack = Stack()

    def __init__(self, func, args=[]):
        super(Function, self).__init__()
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
            self.vars[param[2]] = [VAR(param[1], func[-1][0], arg)]

        if len(params) != 0:
            for param in params:
                if param[0] is 'id':
                    self.declare_cpi(param[2], -1)

        # Func Scope
        self.stack.push(Scope(func[4], ScopeType.FUNC))

    def declare_var(self, var_type, var_name, lineno):
        var = VAR(var_type, lineno)
        if var_name not in self.vars:
            self.vars[var_name] = []
        self.vars[var_name].append(var)

        # For optimization
        self.declare_cpi(var_name, lineno)
        self.add_csi(var_name)

    def get_var(self, var_name):
        if var_name not in self.vars:
            return None
        return self.vars[var_name][-1]

    def release_var(self, var_name):
        self.vars[var_name].pop()
        if len(self.vars[var_name]) == 0:
            self.vars.pop(var_name, None)

        # For optimization
        self.release_cpi(var_name)
        self.del_csi(var_name)


# return finished, value.
# If there's another functcall in expr, it return False, None
# Otherwise return True, value
def next_expr(func, expr, lineno):
    global CURRENT_LINE

    behavior = expr[0]
    if behavior == 'number':
        return True, expr[1]
    elif behavior == 'id':
        var = func.get_var(expr[1])
        if var is None:
            raise PException(f"Variable {expr[1]} not found")
        # TODO: need to fix error
        add_cp_id(func, expr, lineno)

        return True, var.value
    elif behavior == 'functcall':
        scope = func.stack.top()
        if len(scope.dest) != 0:
            expr[:] = ['number', scope.dest[0]]
            scope.dest = scope.dest[1:]
            return next_expr(func, expr, lineno)

        callee, args_info, tmp1, tmp2, lineno = expr[1:]
        # error if functcall function is 'printf' -> this function call value is used for assignment!
        if not callee in FUNCTION_DICT:
            raise PException(f"{callee} function doesn't exist")
        else:
            args_info = args_info[1]
            args = []
            for arg in args_info:
                finished, arg = next_expr(func, arg, lineno)
                if finished:
                    args.append(arg)
            new_func = Function(FUNCTION_DICT[callee], args)
            MAIN_STACK.push(new_func)
            CURRENT_LINE = FUNCTION_DICT[callee][4][0][1] - 1

        next_line()
        return False, None
    elif behavior == 'casting':
        used_vars, expr_str = expr[3:]
        func.access_csi(expr_str, used_vars, lineno, func.get_var)

        finished, value = next_expr(func, expr[2], lineno)
        if not finished:
            return False, None
        if expr[1] == 'int':
            return True, int(value)
        elif expr[1] == 'float':
            return True, float(value)
        raise PException(f"Invalid casting {expr[1]}")
    elif behavior == 'array':
        used_vars, expr_str = expr[3:5]
        func.access_csi(expr_str, used_vars, lineno, func.get_var)

        finished, value = next_expr(func, expr[2], lineno)
        if not finished:
            return None, False

        replaced_str = expr[1] + '[' + str(value) + ']'
        var = func.get_var(replaced_str)
        if var is None:
            raise PException(f"Array has {expr[1][2]}th member")

        add_cp_array(func, replaced_str, lineno)

        return True, var.value
    else:
        used_vars, expr_str = expr[3:5]
        func.access_csi(expr_str, used_vars, lineno, func.get_var)

        finished, value1 = next_expr(func, expr[1], lineno)
        if not finished:
            return False, None

        finished, value2 = next_expr(func, expr[2], lineno)
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


def next_line():
    global CURRENT_LINE

    func = MAIN_STACK.top()
    if func is None:
        return
    
    if isinstance(func, Return):
        value = func.value
        MAIN_STACK.pop()
        # function which called 'functcall' statement
        func = MAIN_STACK.top()
        scope = func.stack.top()
        scope.dest.append(value)
        # put stmt lineno
        CURRENT_LINE = scope.stmts[scope.idx][-1] -1
    else:
        scope = func.stack.top()

    # change current line to first line of for-loop if current line is last line of for-loop
    if isinstance(scope, SubScope) and scope.type == ScopeType.FOR:
        if scope.idx >= len(scope.stmts):
            scope.idx = 2
            CURRENT_LINE = scope.line_no[0] - 1

    stmt = scope.stmts[scope.idx]

    stmt_lineno = stmt[-1]
    if isinstance(stmt_lineno, list):
        stmt_lineno = stmt_lineno[0]

    if CURRENT_LINE >= stmt_lineno:
        scope.idx += 1
        next_line()
        return

    if CURRENT_LINE + 1 < stmt_lineno:
        CURRENT_LINE += 1
        return

    if isinstance(scope, SubScope):
        scope.update_next_idx()

    behavior = stmt[0]
    if behavior in ["{", "}"]:
        lineno = stmt[1]
        CURRENT_LINE = lineno
        scope.idx += 1

    elif behavior == "declare":
        '''
        ['declare', 'int', [
                ['id', ['i'], 'i'],
                ['id', ['total'] 'total']
            ], 2]
        '''
        var_type, var_list, lineno = stmt[1:]
        for var in var_list:
            if var[0] is 'array':
                finished, index_value = next_expr(func, var[2], lineno)
                if not finished:
                    raise PException(f"array cannot be resolved")
            elif var[0] is 'id':
                index_value = 1
            else:
                raise PException(f"wrong declaration")

            for i in range(0, index_value):
                if var[0] is 'array':
                    var_name = var[1] + '[' + str(i) + ']'
                else:
                    var_name = var[1]

                if isinstance(scope, SubScope):
                    if var_name not in scope.declared_vars:
                        scope.declared_vars.append(var_name)
                        func.declare_var(var_type, var_name, lineno)
                    else:
                        if scope.type is ScopeType.FOR:
                            scope.update_idx()
                            next_line()
                        else:
                            raise PException(f"Double declaration in if-statement!")
                else:
                    func.declare_var(var_type, var_name, lineno)
        # Declaration in for-statement invoked once at first.
        CURRENT_LINE = lineno
        scope.idx += 1

    elif behavior == "assign":
        '''
        ['assign', ['id', ['count'], 'count'], expr, 0]
        ['assign', ['array', 'mark', ['id', 'i', ['i'], 'i'], ['mark', 'i'], 'mark[i]'], expr, 1]
        '''
        var_info, expr, lineno = stmt[1:]
        if expr[0] == 'functcall':
            if len(scope.dest) == 0:
                next_expr(func, expr, lineno)
                return

        if var_info[0] is 'id':
            lhs = var_info[1]
        elif var_info[0] is 'array':
            finished, index_value = next_expr(func, var_info[2], lineno)
            if not finished:
                raise PException(f"array cannot be resolved")
            lhs = var_info[1] + '[' + str(index_value) + ']'
        else:
            raise PException(f"assign must be for id or array")

        var = func.get_var(lhs)
        if var is None:
            raise PException(f"Variable {lhs} not found")

        finished, value = next_expr(func, expr, lineno)

        if finished:
            var.assign(value, lineno)
            update_optimization_information_with_assign(func, expr, lineno, lhs)

            if isinstance(scope, SubScope):
                # assignment in for() is executed with other statements which in the same line
                if scope.type is ScopeType.FOR:
                    if lineno == scope.line_no[0]:
                        scope.update_idx()
                        next_line()
                # copy propagation cannot be from inner scope to outer scope
                if not var_info[1] in scope.assigned_vars:
                    scope.assigned_vars.append(lhs)
            CURRENT_LINE = lineno
            scope.idx += 1

    elif behavior == "increment":
        '''
        ['increment', ['id', 'i'], 0]
        '''
        var_info, lineno = stmt[1:]
        var = func.get_var(var_info[1])
        if var is None:
            raise PException(f"Varaible {var_info[1]} not found")
        value = var.value
        var.assign(value + 1, lineno)

        update_optimization_information_with_increment(func, var_info, lineno)

        # increment in for() is executed with other statements which in the same line
        if isinstance(scope, SubScope):
            if scope.type is ScopeType.FOR:
                if lineno == scope.line_no[0]:
                    scope.update_idx()
                    next_line()
        CURRENT_LINE = lineno
        scope.idx += 1

    elif behavior == "for":
        '''
        ['for', ['assign', ['id', 'i'],['number', 0.0, '0.0'], 3],
                ['i', '<', ['id', 'count'], 3],
                ['increment', ['id', 'i'], 3],
                stmts,
                [3, 5]]
        '''
        func.stack.push(SubScope(stmt[1:-1], stmt[-1], ScopeType.FOR))
        next_line()
    elif behavior == "if":
        '''
        ['if', ['average', '>', ['number', 40.0, '40.0'], 21],
               stmts,
               [21, 23]]
        '''
        func.stack.push(SubScope(stmt[1:-1], stmt[-1], ScopeType.IF))
        lineno = stmt[-1][0]
        next_line()

    elif behavior == "functcall":
        '''
        ['functcall', 'printf',
                        ['args', [['string', [], '"%f\\n"'], ['id', ['average'], 'average']]], [
                        22]
        '''
        callee, args_info, ignore, ignore, lineno = stmt[1:]
        if callee == "printf":
            args_info = args_info[1]
            print_format = args_info[0][2]
            args = []
            for arg in args_info[1:]:
                if arg[0] == 'id':
                    var = func.get_var(arg[1])
                    if var is None:
                        raise PException(f"Varaible {args_info[1]} not found")
                    args.append(var.value)
                elif arg[0] == 'array':
                    finished, index_var = next_expr(func, arg[2], lineno)
                    if not finished:
                        PException(f"array index cannot be resolved")
                    var = func.get_var(arg[1] + '[' + str(index_var) + ']')
                    if var is None:
                        raise PException(f"Varaible {args_info[1]} not found")
                    args.append(var.value)
                elif arg[0] == 'number':
                    args.append(arg[1])

            if not IS_IN_OPTIMIZATION:
                print(print_format % tuple(args))

            CURRENT_LINE = lineno
            scope.idx += 1
        else:
            # check whether function is defined function or not
            if not callee in FUNCTION_DICT:
                raise PException(f"{callee} function doesn't exist")
            else:
                args_info = args_info[1]
                args = []
                for arg in args_info:
                    finished, arg = next_expr(func, arg, lineno)
                    if finished:
                        args.append(arg)
                new_func = Function(FUNCTION_DICT[callee], args)
                MAIN_STACK.push(new_func)

            CURRENT_LINE = lineno
            scope.idx += 1
            next_line()

    elif behavior == "return":
        '''
        ['return', ['/', ['id', ['total'], 'total'], ['id', ['count'], 'count']], 6]
        '''
        # use 'Return' class
        # Remove currently running function stack
        expr, lineno = stmt[1:]
        MAIN_STACK.pop()
        success, value = next_expr(func, expr, lineno)
        MAIN_STACK.push(Return(value))
        scope.idx += 1
        CURRENT_LINE = lineno

    elif behavior == "condition":
        '''
        ['condition', 'a', '>', ['number', 0.0, [0.0], '0.0'], 3]
        '''
        success, right_value = next_expr(func, stmt[3], stmt[4])
        if not success:
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
            raise PException(f"condition({condition}) is invalid", stmt[4])
        CURRENT_LINE = stmt[-1]

    if isinstance(scope, SubScope):
        scope.update_idx()

    while not MAIN_STACK.isEmpty():
        func = MAIN_STACK.top()

        if isinstance(func, Return):
            return 

        if func.stack.isEmpty():
            MAIN_STACK.pop()
            continue

        scope = func.stack.top()
        if scope.is_done():
            if isinstance(scope, SubScope):
                CURRENT_LINE = scope.line_no[1]
                remove_optimization_information_with_scope(func, scope, CURRENT_LINE)
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


def interpret_initialization(tree):
    global CURRENT_LINE

    # Function index
    for func_info in tree:
        FUNCTION_DICT[func_info[2]] = func_info

    if "main" not in FUNCTION_DICT:
        raise PException("Main function doesn't exist")

    MAIN_STACK.push(Function(FUNCTION_DICT["main"]))
    CURRENT_LINE = FUNCTION_DICT["main"][4][0][1] - 1


def interpret(tree):
    global CURRENT_LINE

    interpret_initialization(tree)
    while not MAIN_STACK.isEmpty():
        cmd = ""
        while True:
            cmd = input("Input Command(next [number] / print [variable] / trace [variable]): ").strip().split(" ")
            if cmd == ["next"]:
                cmd = ["next", "1"]

            if len(cmd) != 2:
                continue
            if cmd[0] not in ["next", "print", "trace"]:
                continue
            if cmd[0] == "next" and not cmd[1].isdigit():
                continue
            break

        if cmd[0] == "next":
            cnt = int(cmd[1])
            while cnt > 0:
                next_line()
                # CURRENT_LINE += 1
                cnt -= 1

        elif cmd[0] == "print":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var is None:
                print(f"Variable {cmd[1]} not found")
            else:
                print(f"Value of {cmd[1]}: {var.value}")

        elif cmd[0] == "trace":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var is None:
                print(f"Variable {cmd[1]} not found")
            else:
                print(f"History of {cmd[1]}")
                for history in var.history:
                    print(f"{cmd[1]} = {history[1]} at line {history[0]}")

        if CURRENT_LINE >= len(PLAIN_CODE):
            break

        # TODO : this line is for debug
        print(f"Current stmt: (Line {CURRENT_LINE}) {PLAIN_CODE[CURRENT_LINE]}")
    print("End of Program")


def process():
    tree = get_parser_tree(PLAIN_CODE_ONE_LINE)
    interpret(tree)


def load_input_file(filename):
    f = open(f"inputs/{filename}", "r")

    lines = f.readlines()
    # lines[1] indicates Line 1
    lines.insert(0, "")

    f.close()

    return lines, "".join(lines)


def process_without_input():
    global MAIN_STACK
    global CURRENT_LINE
    global CP_DICT
    global CS_DICT
    global FUNCTION_DICT

    # initialize
    MAIN_STACK = Stack()
    CURRENT_LINE = 0
    CP_DICT = {}
    CS_DICT = {}
    FUNCTION_DICT = {}

    # process whole lines
    tree = get_parser_tree(PLAIN_CODE_ONE_LINE)
    interpret_initialization(tree)

    while not MAIN_STACK.isEmpty():
        next_line()


def print_optimized_code():
    global PLAIN_CODE
    global PLAIN_CODE_ONE_LINE
    global IS_IN_OPTIMIZATION

    IS_IN_OPTIMIZATION = True
    PLAIN_CODE, PLAIN_CODE_ONE_LINE = get_cp_optimized_code(PLAIN_CODE)
    process_without_input()
    PLAIN_CODE,PLAIN_CODE_ONE_LINE = get_cs_optimized_code(PLAIN_CODE)

    # write optimized code
    f = open("output.c", "w")
    f.writelines(PLAIN_CODE)
    f.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_filename = sys.argv[1]
    else:
        input_filename = "function_call7.c"

    try:
        PLAIN_CODE, PLAIN_CODE_ONE_LINE = load_input_file(input_filename)
        process()
    except PException as e:
        print("Compile Error: ", e)

    print_optimized_code()
