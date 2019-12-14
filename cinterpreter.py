from cyacc import get_parser_tree
from coptimization import *
import ast
import copy
import enum
import sys

DEBUG = False


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
    def __init__(self, var_type, is_array, lineno, value=None):
        self.type = var_type
        self.is_array = is_array
        self.value = value
        self.history = [[lineno, value]]

    def assign(self, value, lineno, index=None):
        if "int" in self.type:
            value = int(value)
        if "float" in self.type:
            value = float(value)

        if self.is_array:
            new_value = copy.deepcopy(self.value)
            new_value[index] = value
        else:
            new_value = value

        self.history.append([lineno, new_value])
        self.value = new_value
    
    def increment(self, lineno, index=None):
        if self.is_array:
            new_value = copy.deepcopy(self.value)
            new_value[index] = new_value[index] + 1
        else:
            new_value = self.value + 1
        
        self.history.append([lineno, new_value])
        self.value = new_value


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
        self.declared_vars = []

        self.lineno = [self.stmts[0][1]["lineno"], self.stmts[-1][1]["lineno"]]
    
    def update_idx(self):
        self.idx += 1
    
    def is_done(self):
        return self.idx == len(self.stmts)


class ForScope(Scope):
    def __init__(self, for_info, func):
        # stmts: [assign, increment, condition, ..stmts..]
        super(ForScope, self).__init__([for_info["assign"], for_info["increment"], for_info["condition"]] + for_info["stmts"], ScopeType.FOR)
        self.original_stmts = copy.deepcopy(self.stmts)
        self.done = False
        self.func = func

    def init(self):
        self.stmts = copy.deepcopy(self.original_stmts)

    def update_idx(self):
        if self.idx == 0:
            self.idx = 2
        elif self.idx == len(self.stmts) - 1:
            self.idx = 1
            self.release_vars()
        else:
            self.idx += 1

    def set_done(self):
        self.done = True

    def is_done(self):
        return self.done

    def release_vars(self):
        for var in self.declared_vars:
            self.func.release_var(var)


class IfScope(Scope):
    def __init__(self, if_info, func):
        super(IfScope, self).__init__([if_info["condition"]] + if_info["stmts"], ScopeType.IF)
        self.done = False
        self.func = func
    
    def set_done(self):
        self.done = True
    
    def is_done(self):
        return self.done or self.idx == len(self.stmts)

    def release_vars(self):
        for var in self.declared_vars:
            self.func.release_var(var)


class Function(Optimization):
    def __init__(self):
        super(Function, self).__init__()
        self.vars = {}
        self.stack = Stack()

    def __init__(self, func, args=[]):
        super(Function, self).__init__()
        self.vars = {}
        self.stack = Stack()

        content = func[1]

        name = content["name"]
        # Argument
        params = content["params"]
        lineno = content["lineno"]

        expected_args_length = 0
        if len(params) != 0 and params != ["void"] and params != [None]:
            expected_args_length = len(params)
            if "void" in params:
                raise CException(f"Function {name}'void' must be the first and only parameter if specified")
        else:
            params = []

        if expected_args_length != len(args):
            raise CException(f"Function {name}, expected {expected_args_length} arguments, but {len(args)} given")

        for param, arg in zip(params, args):
            self.vars[param[1]["name"]] = [VAR(param[1]["type"], isinstance(arg, list), lineno[0], arg)]

        if len(params) != 0:
            for param in params:
                if param[0] is 'id':
                    self.declare_cpi(param[1]["name"], -1)

        # Func Scope
        self.stack.push(Scope(content["stmts"], ScopeType.FUNC))

    def declare_var(self, var_type, var_name, lineno, value=None):
        var = VAR(var_type, isinstance(value, list), lineno, value)
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

    if expr is None:
        return True, None

    behavior, content = expr
    if behavior == 'number':
        return True, content["value"]
    elif behavior == 'id':
        var = func.get_var(content["name"])
        if var is None:
            raise CException(f"Variable {content['name']} not found")
        add_cp_id(func, content["name"], lineno)

        return True, var.value
    elif behavior == 'functcall':
        callee = content["callee"]
        args_info = content["args"]
        lineno = content["lineno"]

        if callee not in FUNCTION_DICT:
            raise CException(f"{callee} function doesn't exist")
        success = True
        args = []
        for arg in args_info:
            finished, value = next_expr(func, arg, lineno)
            if not finished:
                success = False
                break
            args.append(value)
        if not success:
            return False, None

        scope = func.stack.top()
        expr[:] = []
        scope.dest = expr
        new_func = Function(FUNCTION_DICT[callee], args)
        MAIN_STACK.push(new_func)

        CURRENT_LINE = FUNCTION_DICT[callee][1]["lineno"][0]
        return False, None
    elif behavior == 'casting':
        func.access_csi(content["str"], content["arg_list"], lineno, func.get_var)
        finished, value = next_expr(func, content["expr"], lineno)
        if not finished:
            return False, None
        if content["type"] == "int":
            return True, int(value)
        elif content["type"] == "float":
            return True, float(value)
        raise CException(f"Invalid casting {expr[1]}")
    elif behavior == 'array':
        # TODO : optimization with array
        #var_info = content["index"][1]
        #func.access_csi(var_info["str"], var_info["arg_list"], lineno, func.get_var)
        finished, index = next_expr(func, content["index"], lineno)
        if not finished:
            return None, False
        
        var = func.get_var(content["name"])
        if var is None:
            raise CException(f"Variable {content['name']} not found")

        # TODO : optimization with array
        #replaced_str = f"{content['name']}[{var_info['str']}]"
        #add_cp_array(func, replaced_str, lineno)

        return True, var.value[index]
    else:
        func.access_csi(content["str"], content["arg_list"], lineno, func.get_var)

        finished, value1 = next_expr(func, content["lhs"], lineno)
        if not finished:
            return False, None

        finished, value2 = next_expr(func, content["rhs"], lineno)
        if not finished:
            return False, None

        value = None
        op = content["op"]
        if op == '+':
            value = value1 + value2
        elif op == '-':
            value = value1 - value2
        elif op == '/':
            if value2 == 0:
                raise CException("Division by zero")
            value = value1 / value2
        elif op == '*':
            value = value1 * value2
        else:
            raise CException(f"Invalid operator {expr[0]}")
        return True, value


def execute_line():
    global CURRENT_LINE
    # Execute CURRENT_LINE
    
    line_printed = False

    while True:
        func = MAIN_STACK.top()
        if func is None:
            return

        has_return_value = False
        return_value = None
        if isinstance(func, Return):
            return_value = func.value
            MAIN_STACK.pop()
            func = MAIN_STACK.top()
            has_return_value = True

        scope = func.stack.top()
        stmt = scope.stmts[scope.idx]

        behavior, content = stmt

        stmt_lineno = content["lineno"]
        if isinstance(stmt_lineno, list):
            stmt_lineno = stmt_lineno[0]

        if has_return_value:
            if return_value is not None:
                scope.dest.extend(["number", {"value": return_value}])
            CURRENT_LINE = stmt_lineno

            scope.dest = [] #reset

        if DEBUG and not line_printed:
            line_printed = True
            print(f"Line {CURRENT_LINE}: {PLAIN_CODE[CURRENT_LINE]}")

        # For Empty line
        if CURRENT_LINE != stmt_lineno:
            break

        if behavior in ["{", "}"]:
            pass

        elif behavior == "declare":
            '''
            ['declare', {
                    'type': 'int',
                    'vars': [
                    ['id', {
                        'name': 'c',
                        'arg_list': ['c'],
                        'str': 'c',
                        'lineno': 8
                    }],
                    ['array', {
                        'name': 'c',
                        'index': ['number', {
                            'value': 4,
                            'arg_list': [],
                            'str': '4',
                            'lineno': 4
                        }],
                        'arg_list': ['c'],
                        'str': 'c[4]',
                        'lineno': 4
                    }]
                    ],
                    'lineno': 8
            }]
            '''
            var_type = content["type"]
            var_list = content["vars"]
            lineno = content["lineno"]
            for var_info in var_list:
                var_name = var_info[1]["name"]
                value = None

                if var_info[0] == "array":
                    finished, size = next_expr(func, var_info[1]["index"], lineno)
                    if not finished:
                        raise CException("Array cannot be resolved")

                    value = [None] * size

                if not var_name in scope.declared_vars:
                    scope.declared_vars.append(var_name)
                func.declare_var(var_type, var_name, lineno, value)

        elif behavior == "assign":
            '''
            ['assign', {
                    'var': ['array', {
                        'name': 'c',
                        'index': ['number', {
                            'value': 0,
                            'arg_list': [],
                            'str': '0',
                            'lineno': 7
                        }],
                        'arg_list': ['c'],
                        'str': 'c[0]',
                        'lineno': 7
                        }],
                    'expr': ['number', {
                        'value': 3,
                        'arg_list': [],
                        'str': '3',
                        'lineno': 7
                        }],
                    'lineno': 7
                }]
            '''
            var_info = content["var"]
            expr = content["expr"]
            lineno = content["lineno"]

            index = None
            var_name = var_info[1]["name"]
            if var_info[0] == "array":
                finished, index = next_expr(func, var_info[1]["index"], lineno)
                if not finished:
                    raise CException("Array cannot be resolved")
            
            var = func.get_var(var_name)
            if var is None:
                raise CException(f"Variable {var_name} not found")

            finished, value = next_expr(func, expr, lineno)
            if finished:
                var.assign(value, lineno, index)
                update_optimization_information_with_assign(func, expr, lineno, var_name)
            else:
                return

        elif behavior == "increment":
            '''
            ['increment', {
                    'var': ['id', {
                        'name': 'b',
                        'arg_list': ['b'],
                        'str': 'b',
                        'lineno': 7
                        }],
                    'lineno': 0
                }]
            '''
            var_info = content["var"]
            lineno = content["lineno"]

            var_name = var_info[1]["name"]
            index = None
            if var_info[0] == "array":
                finished, index = next_expr(func, var_info[1], lineno)
                if not finished:
                    raise CException("Array cannot be resolved")

            var = func.get_var(var_name)
            if var is None:
                raise CException(f"Variable {var_name} not found")

            var.increment(lineno, index)

            update_optimization_information_with_increment(func, var_name, lineno)

        elif behavior == "for":
            '''
            ['for', {
                'assign': ['assign', {
                'var': ['id', {
                    'name': 'i',
                    'arg_list': ['i'],
                    'str': 'i',
                    'lineno': 21
                }],
                'expr': ['number', {
                    'value': 0,
                    'arg_list': [],
                    'str': '0',
                    'lineno': 21
                }],
                'lineno': 21
                }],
                'condition': ['condition', {
                'var': 'i',
                'cmp': '<',
                'expr': ['number', {
                    'value': 5,
                    'arg_list': [],
                    'str': '5',
                    'lineno': 21
                }],
                'lineno': 21
                }],
                'increment': ['increment', {
                'var': ['id', {
                    'name': 'i',
                    'arg_list': ['i'],
                    'str': 'i',
                    'lineno': 21
                }],
                'lineno': 21
                }],
                'stmts': [...],
                'lineno': [21, 30]
            }]
            '''
            func.stack.push(ForScope(content, func))
            continue

        elif behavior == "if":
            '''
            ['if', {
                'condition': ['condition', {
                'var': 'k',
                'cmp': '>',
                'expr': ['number', {
                    'value': 6,
                    'arg_list': [],
                    'str': '6',
                    'lineno': 27
                }],
                'lineno': 27
                }],
                'stmts': [...],
                'lineno': [27, 29]
            }]
            '''
            func.stack.push(IfScope(content, func))
            continue

        elif behavior == "functcall":
            '''
            ['functcall', {
                    'callee': 'printf',
                    'args': [
                    ['string', {
                        'arg_list': [],
                        'str': '"%d\\n%d\\n"',
                        'lineno': 12
                    }],
                    ['id', {
                        'name': 'a',
                        'arg_list': ['a'],
                        'str': 'a',
                        'lineno': 12
                    }],
                    ['id', {
                        'name': 'b',
                        'arg_list': ['b'],
                        'str': 'b',
                        'lineno': 12
                    }]
                    ],
                    'arg_list': ['a', 'b'],
                    'str': 'f("%d\\n%d\\n",a,b',
                    'lineno': 12
                }]
            '''
            callee = content["callee"]
            args_info = content["args"]
            lineno = content["lineno"]

            if callee == "printf":
                printf_format = ast.literal_eval(args_info[0][1]["str"])
                success = True
                args = []
                for arg in args_info[1:]:
                    finished, value = next_expr(func, arg, lineno)
                    if not finished:
                        success = False
                        break
                    args.append(value)

                if not success:
                    return

                if not get_is_in_optimization():
                    print(printf_format % tuple(args))
            else:
                if not callee in FUNCTION_DICT:
                    raise CException(f"{callee} function doesn't exist")

                success = True
                args = []
                for arg in args_info:
                    finished, value = next_expr(func, arg, lineno)
                    if not finished:
                        success = False
                        break
                    args.append(value)
                if not success:
                    return
                stmt[:] = ["called", {"lineno": lineno}]
                new_func = Function(FUNCTION_DICT[callee], args)
                MAIN_STACK.push(new_func)

                CURRENT_LINE = FUNCTION_DICT[callee][1]["lineno"][0]
                return

        elif behavior == "return":
            '''
            ['return', {
                    'value': ['id', {
                        'name': 'a',
                        'arg_list': ['a'],
                        'str': 'a',
                        'lineno': 2
                    }],
                    'lineno': 2
                }]
            '''
            # use 'Return' class
            # Remove currently running function stack
            expr = content["value"]
            lineno = content["lineno"]

            finished, value = next_expr(func, expr, lineno)
            if not finished:
                return

            MAIN_STACK.pop()
            MAIN_STACK.push(Return(value))
            return

        elif behavior == "condition":
            '''
            ['condition', {
              'var': 'k',
              'cmp': '>',
              'expr': ['number', {
                'value': 6,
                'arg_list': [],
                'str': '6',
                'lineno': 27
              }],
              'lineno': 27
            }]
            '''
            expr = content["expr"]
            lineno = content["lineno"]
            success, right_value = next_expr(func, expr, lineno)
            if not success:
                return

            var = func.get_var(content["var"])
            if var is None:
                raise CException(f"Variable {content['var']} not found")
            left_value = var.value
            if left_value is None:
                raise CException(f"Varaible {content['var']} is not assigned yet")
            condition = content["cmp"]

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
                raise CException(f"condition({condition}) is invalid", stmt[4])

        scope.update_idx()

        while not MAIN_STACK.isEmpty():
            func = MAIN_STACK.top()
            if func.stack.isEmpty():
                MAIN_STACK.pop()
                continue

            scope = func.stack.top()
            if scope.is_done():
                CURRENT_LINE = scope.lineno[1]
                func.stack.pop()
                next_scope = func.stack.top()
                if next_scope is not None:
                    next_scope.update_idx()
                if isinstance(scope, IfScope):
                    scope.release_vars()
                continue
            break

    if isinstance(scope, ForScope) and scope.idx == 1:
        CURRENT_LINE = scope.lineno[0]
        scope.init()
    else:
        CURRENT_LINE += 1


def interpret_initialization(tree):
    global CURRENT_LINE

    # Function index
    for func_info in tree:
        FUNCTION_DICT[func_info[1]["name"]] = func_info

    if "main" not in FUNCTION_DICT:
        raise CException("Main function doesn't exist")

    MAIN_STACK.push(Function(FUNCTION_DICT["main"]))
    CURRENT_LINE = FUNCTION_DICT["main"][1]["lineno"][0]


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
                print("Incorrect command usage: try 'next [lines]")
                continue
            break

        if cmd[0] == "next":
            cnt = int(cmd[1])
            while cnt > 0 and not MAIN_STACK.isEmpty():
                execute_line()
                cnt -= 1

        elif cmd[0] == "print":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var is None:
                print(f"Invisible variable")
            else:
                value = "N/A" if var.value is None else var.value
                print(f"Value of {cmd[1]}: {var.value}")

        elif cmd[0] == "trace":
            func = MAIN_STACK.top()
            var = func.get_var(cmd[1])
            if var is None:
                print(f"Invisible variable")
            else:
                print(f"History of {cmd[1]}")
                for history in var.history:
                    value = "N/A" if history[1] is None else history[1]
                    print(f"{cmd[1]} = {value} at line {history[0]}")

        if CURRENT_LINE >= len(PLAIN_CODE):
            break

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
    global FUNCTION_DICT

    # initialize
    MAIN_STACK = Stack()
    CURRENT_LINE = 0
    FUNCTION_DICT = {}
    initialize_optimization()

    # process whole lines
    tree = get_parser_tree(PLAIN_CODE_ONE_LINE)
    interpret_initialization(tree)

    while not MAIN_STACK.isEmpty():
        execute_line()


def print_optimized_code():
    global PLAIN_CODE
    global PLAIN_CODE_ONE_LINE

    PLAIN_CODE, PLAIN_CODE_ONE_LINE = get_cp_optimized_code(PLAIN_CODE)
    if DEBUG:
        for line in PLAIN_CODE:
            print(line)
    process_without_input()
    PLAIN_CODE, PLAIN_CODE_ONE_LINE = get_cs_optimized_code(PLAIN_CODE)

    # write optimized code
    f = open("output.c", "w")
    f.writelines(PLAIN_CODE)
    f.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_filename = sys.argv[1]
    else:
        input_filename = "input0.c"

    try:
        PLAIN_CODE, PLAIN_CODE_ONE_LINE = load_input_file(input_filename)
        process()
    except CException as e:
        print("Compile Error: ", e)

    print_optimized_code()
