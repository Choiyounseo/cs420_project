from cyacc import get_parser_tree
import copy
import enum
import sys
import re


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
PLAIN_CODE_ONE_LINE = ""
CURRENT_LINE = 0
# Copy Propagation
# key : (line number, before variable), value : next variable
CP_LIST = {}
# Common Subexpression Elimination
# key : target expression, value : (variable type, target line numbers of sets) of list
CS_DICT = {}
IS_IN_OPTIMIZATION = False


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


# Copy Propagation Information
class CPI:
    def __init__(self, lineno):
        # rhs can be variable or direct number
        self.rhs = None
        self.lineno = lineno

    def assign(self, new_rhs, new_lineno):
        self.rhs = new_rhs
        self.lineno = new_lineno


# Common Subexpression Elimination Information
class CSI:
    def __init__(self, used_vars, lineno):
        self.used_vars = used_vars
        self.lines = [lineno]

    def assign(self, lineno):
        self.lines[-1] = lineno

    def add_line(self, new_line):
        self.lines.append(new_line)


class ScopeType(enum.Enum):
    FUNC = 0
    IF = 1
    FOR = 2


class Scope:
    def __init__(self, stmts, type):
        self.stmts = copy.deepcopy(stmts)
        self.type = type
        self.idx = 0
        self.dest = None  # Where the return value had to be located

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
                if self.next_idx >= len(self.stmts):
                    self.next_idx = 2

    def set_done(self):
        self.is_condition_true = False

    def is_done(self):
        return not self.is_condition_true


class Function:
    def __init__(self):
        self.vars = {}
        self.cpis = {}
        self.csis = {}
        self.stack = Stack()

    def __init__(self, func, args=[]):
        self.vars = {}
        self.cpis = {}
        self.csis = {}
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

    def declare_cpi(self, var_name, lineno):
        cpi = CPI(lineno)
        if var_name not in self.cpis:
            self.cpis[var_name] = []
        self.cpis[var_name].append(cpi)

    def get_cpi(self, var_name):
        if var_name not in self.cpis:
            return None
        return self.cpis[var_name][-1]

    def release_cpi(self, var_name):
        self.cpis[var_name].pop()
        if len(self.cpis[var_name]) == 0:
            self.cpis.pop(var_name, None)

    def access_csi(self, expr_str, used_var, lineno):
        if expr_str not in self.csis:
            self.csis[expr_str] = [CSI(used_var, lineno)]
        elif self.csis[expr_str][-1].lines[-1] is -1:
            self.csis[expr_str][-1].assign(lineno)
        else:
            self.csis[expr_str][-1].add_line(lineno)
            if len(used_var) > 0:
                var = self.get_var(used_var[0])
                if var is not None:
                    add_cs(var.type, expr_str, self.csis[expr_str][-1].lines)

    def add_csi(self, var):
        for expr_str in self.csis:
            for arg in self.csis[expr_str][-1].used_vars:
                if arg is var:
                    csi = CSI(self.csis[expr_str][-1].used_vars, -1)
                    self.csis[expr_str].append(csi)

    def del_csi(self, var):
        remove_list = []
        for expr_str in self.csis:
            for arg in self.csis[expr_str][-1].used_vars:
                if arg == var:
                    if expr_str not in remove_list:
                        remove_list.append(expr_str)
                    break
        for expr_str in remove_list:
            self.release_csi(expr_str)

    def get_csi(self, expr_str):
        if expr_str not in self.csis:
            return None
        return self.csis[expr_str][-1]

    def release_csi(self, expr_str):
        self.csis[expr_str].pop()
        if len(self.csis[expr_str]) == 0:
            self.csis.pop(expr_str, None)


def add_cp_id(func, expr, lineno):
    global CP_LIST

    cpi = func.get_cpi(expr[1])
    if cpi is None:
        raise PException(f"Declared variable {expr[1]} doesn't have cpi")

    if cpi.rhs is None:
        return

    CP_LIST[(lineno, expr[1])] = cpi.rhs


def add_cp_array(func, replaced_str, lineno):
    global CP_LIST

    cpi = func.get_cpi(replaced_str)
    if cpi is None:
        raise PException(f"{replaced_str} doesn't have cpi")

    if cpi.rhs is None:
        return

    CP_LIST[(lineno, replaced_str)] = cpi.rhs


def add_cs(expr_type, expr_str, target_lines):
    global CS_DICT

    if len(target_lines) <= 1:
        return

    if expr_str not in CS_DICT:
        CS_DICT[expr_str] = []

    is_overriding = False
    for (index, (expr_type, lines)) in enumerate(CS_DICT[expr_str]):
        if lines.issubset(target_lines):
            CS_DICT[expr_str][index] = (expr_type, set(target_lines))
            is_overriding = True
            break

    if not is_overriding:
        CS_DICT[expr_str].append((expr_type, set(target_lines)))


def update_optimization_information_with_assign(func, scope, var_info, expr, lineno, lhs):
    cpi = func.get_cpi(lhs)

    # direct assignment
    if expr[0] is 'number':
        cpi.assign(expr[1], lineno)
    elif expr[0] is 'id':
        cpi.assign(expr[1], lineno)
    # cpi should be erased if not direct assignment
    else:
        cpi.assign(None, lineno)

    # cpi should be deleted if it has just assigned variable as rhs
    for var_name in func.cpis:
        if func.cpis[var_name][-1].rhs is lhs:
            func.cpis[var_name][-1].assign(None, lineno)

    for expr_str in func.csis:
        if lhs in func.csis[expr_str][-1].used_vars:
            func.csis[expr_str][-1].lines = [-1]

    if isinstance(scope, SubScope):
        # assignment in for() is executed with other statements which in the same line
        if scope.type is ScopeType.FOR:
            if lineno == scope.line_no[0]:
                scope.update_idx()
                next_line()
        # copy propagation cannot be from inner scope to outer scope
        if not var_info[1] in scope.assigned_vars:
            scope.assigned_vars.append(lhs)


def remove_optimization_information(func, var_info, lineno):
    # cpi should be erased if it has just assigned variable as rhs
    for var_name in func.cpis:
        if func.cpis[var_name][-1].rhs is var_info[1]:
            func.cpis[var_name][-1].assign(None, lineno)


def remove_optimization_information_with_scope(func, scope):
    for var in scope.assigned_vars:
        func.cpis[var][-1].assign(None, CURRENT_LINE)


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

        add_cp_id(func, expr, lineno)

        return True, var.value
    elif behavior == 'functcall':
        used_vars, expr_str = expr[3:5]
        func.access_csi(expr_str, used_vars, lineno)

        func.dest = []
        # TODO: push to the stack for functcall
        expr = func.dest
        return None, False
    elif behavior == 'casting':
        used_vars, expr_str = expr[3:]
        func.access_csi(expr_str, used_vars, lineno)

        finished, value = next_expr(func, expr[2], lineno)
        if not finished:
            return False, None
        if expr[1] == 'int':
            return True, int(value)
        elif expr[1] == 'float':
            return True, float(value)
        raise PException(f"Invalid casting {expr[1]}")
    elif behavior == 'array':
        used_vars, expr_str = expr[3:]
        func.access_csi(expr_str, used_vars, lineno)

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
        used_vars, expr_str = expr[3:]
        func.access_csi(expr_str, used_vars, lineno)
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

    scope = func.stack.top()

    CURRENT_LINE += 1
    stmt = scope.stmts[scope.idx]

    stmt_lineno = stmt[-1]
    if isinstance(stmt_lineno, list):
        stmt_lineno = stmt_lineno[0]
    if CURRENT_LINE < stmt_lineno:
        return

    if isinstance(scope, SubScope):
        scope.update_next_idx()

    behavior = stmt[0]
    if behavior in ["{", "}"]:
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
        # CURRENT_LINE = lineno + skip
        scope.idx += 1

    elif behavior == "assign":
        '''
        ['assign', ['id', ['count'], 'count'], expr, 0]
        ['assign', ['array', 'mark', ['id', 'i', ['i'], 'i'], ['mark', 'i'], 'mark[i]'], expr, 1]
        '''
        var_info, expr, lineno = stmt[1:]
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
            update_optimization_information_with_assign(func, scope, var_info, expr, lineno, lhs)
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

        remove_optimization_information(func, var_info, lineno)

        # increment in for() is executed with other statements which in the same line
        if isinstance(scope, SubScope):
            if scope.type is ScopeType.FOR:
                if lineno == scope.line_no[0]:
                    scope.update_idx()
                    next_line()
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
            scope.idx += 1

    elif behavior == "return":
        '''
        ['return', ['/', ['id', ['total'], 'total'], ['id', ['count'], 'count']], 6]
        '''
        pass

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
                remove_optimization_information_with_scope(func, scope)
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
    func = {}
    for func_info in tree:
        func[func_info[2]] = func_info

    if "main" not in func:
        raise PException("Main function doesn't exist")

    MAIN_STACK.push(Function(func["main"]))
    CURRENT_LINE = func["main"][-1][0]


def interpret(tree):
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


def process_without_input():
    global MAIN_STACK
    global CURRENT_LINE
    global CP_LIST
    global CS_DICT

    # initialize
    MAIN_STACK = Stack()
    CURRENT_LINE = 0
    CP_LIST = {}
    CS_DICT = {}

    # process whole lines
    tree = get_parser_tree(PLAIN_CODE_ONE_LINE)
    interpret_initialization(tree)

    while not MAIN_STACK.isEmpty():
        next_line()


def load_input_file(filename):
    f = open(f"inputs/{filename}", "r")

    lines = f.readlines()
    # lines[1] indicates Line 1
    lines.insert(0, "")

    f.close()

    return lines, "".join(lines)


def get_optimized_cp_string(target_line, target_variables):
    # get right expression
    assign_index = target_line.find('=')
    right_expression = target_line[assign_index + 1:]

    # find target variables
    if '[' in target_variables:
        new_target = target_variables.replace('[', '\[')
        new_target = new_target.replace(']', '\]')
        regex_iter = re.finditer(new_target, right_expression)
    else:
        regex = re.compile(r'([a-zA-Z_][0-9a-zA-Z_]*)')
        regex_iter = regex.finditer(right_expression)

    target_string = []
    for obj in regex_iter:
        if obj.group() == target_variables:
            start_index, end_index = obj.span()
            target_string.append((start_index + assign_index + 1, end_index + assign_index + 1))
    return target_string


def get_indentation_string(target_string):
    regex = re.compile(r'([a-zA-Z_][0-9a-zA-Z_]*)')
    regex_search = regex.search(target_string)
    return target_string[:regex_search.start()]


def get_cs_delta_line(lines, line):
    for line_number in lines:
        if line >= line_number:
            line += 2
    return line


def get_optimized_cs_string(target_line, target_expression, cs_variable):
    # get right expression
    assign_index = target_line.find('=')
    right_expression = target_line[assign_index + 1:]
    right_expression = right_expression.replace(" ", "")
    target_expression = target_expression.replace("*", "\*")
    target_expression = target_expression.replace("+", "\+")

    # find target variables
    if '[' in target_expression:
        # TODO : array
        return target_line

    delta_index = 0
    new_expression = str(right_expression)
    for obj in re.finditer(target_expression, right_expression):
        start_index, end_index = (obj.span()[0] + delta_index, obj.span()[1] + delta_index)
        new_expression = f"{new_expression[:start_index]}{cs_variable}{new_expression[end_index:]}"
        delta_index += len(cs_variable) - (end_index - start_index)
    return f"{target_line[:assign_index + 1]} {new_expression}"


def get_cp_optimized_code():
    new_code = list(PLAIN_CODE)
    for (key, next_variable) in CP_LIST.items():
        line_number, before_variable = key
        target_line = str(new_code[line_number])

        # find target string
        target_string = get_optimized_cp_string(target_line, before_variable)

        # replace
        delta_index = 0
        for start_index, end_index in target_string:
            target_line = f"{target_line[:start_index + delta_index]}{str(next_variable)}{target_line[end_index + delta_index:]}"
            delta_index += len(str(next_variable)) - (end_index - start_index)

        new_code[line_number] = target_line

    return new_code, "".join(new_code)


def get_cs_optimized_code():
    target = sorted(CS_DICT.items(), key=lambda element: len(element[0]), reverse=True)
    new_code = list(PLAIN_CODE)
    inserted_line_numbers = []
    variable_index = 0
    for (index, (target_expression, target_line_info)) in enumerate(target):
        for (target_type, target_line_numbers) in target_line_info:
            target_line_numbers = sorted(list(target_line_numbers))
            if len(target_line_numbers) < 2:
                continue

            # insert variable
            target_line_number = get_cs_delta_line(inserted_line_numbers, target_line_numbers[0])
            indentation = get_indentation_string(new_code[target_line_number])
            variable_name = f"__optimized_variable{variable_index}"

            declare_string = f"{indentation}{target_type} {variable_name};\n"
            assign_string = f"{indentation}{variable_name} = {target_expression};\n"

            new_code.insert(target_line_number, assign_string)
            new_code.insert(target_line_number, declare_string)
            inserted_line_numbers.append(target_line_number)

            # replace variable
            for line_number in target_line_numbers:
                target_line_number = get_cs_delta_line(inserted_line_numbers, line_number)
                new_code[target_line_number] = get_optimized_cs_string(str(new_code[target_line_number]), target_expression, variable_name)

            variable_index += 1

    return new_code, "".join(new_code)


def print_optimized_code():
    global PLAIN_CODE
    global PLAIN_CODE_ONE_LINE
    global IS_IN_OPTIMIZATION

    IS_IN_OPTIMIZATION = True
    PLAIN_CODE, PLAIN_CODE_ONE_LINE = get_cp_optimized_code()
    process_without_input()
    PLAIN_CODE,PLAIN_CODE_ONE_LINE = get_cs_optimized_code()

    # write optimized code
    f = open("output.c", "w")
    f.writelines(PLAIN_CODE)
    f.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_filename = sys.argv[1]
    else:
        input_filename = "common_subexpression_elimination1.c"

    try:
        PLAIN_CODE, PLAIN_CODE_ONE_LINE = load_input_file(input_filename)
        process()
    except PException as e:
        print("Compile Error: ", e)

    print_optimized_code()
