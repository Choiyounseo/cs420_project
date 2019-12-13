import re

# Copy Propagation
# key : (line number, before variable), value : next variable
CP_DICT = {}
# Common Subexpression Elimination
# key : target expression, value : (variable type, target line numbers of sets) of list
CS_DICT = {}

IS_IN_OPTIMIZATION = False


class CException(Exception):
    def __init__(self, msg, lineno=None):
        if lineno is None:
            Exception.__init__(self, msg)
        else:
            Exception.__init__(self, f"[Line {lineno}] {msg}")


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


class Optimization:
    def __init__(self):
        self.cpis = {}
        self.csis = {}

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

    def access_csi(self, expr_str, used_var, lineno, get_var):
        if expr_str not in self.csis:
            self.csis[expr_str] = [CSI(used_var, lineno)]
        elif self.csis[expr_str][-1].lines[-1] is -1:
            self.csis[expr_str][-1].assign(lineno)
        else:
            self.csis[expr_str][-1].add_line(lineno)
            if len(used_var) > 0:
                var = get_var(used_var[0])
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
    global CP_DICT
    cpi = func.get_cpi(expr[1])
    if cpi is None:
        raise CException(f"Declared variable {expr[1]} doesn't have cpi")

    if cpi.rhs is None:
        if (lineno, expr[1]) in CP_DICT:
            del CP_DICT[(lineno, expr[1])]
        return

    CP_DICT[(lineno, expr[1])] = cpi.rhs


def add_cp_array(func, replaced_str, lineno):
    global CP_DICT

    cpi = func.get_cpi(replaced_str)
    if cpi is None:
        raise CException(f"{replaced_str} doesn't have cpi")

    if cpi.rhs is None:
        if (lineno, replaced_str) in CP_DICT:
            del CP_DICT[(lineno, replaced_str)]
        return

    CP_DICT[(lineno, replaced_str)] = cpi.rhs


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


def update_optimization_information_with_assign(func, expr, lineno, lhs):
    cpi = func.get_cpi(lhs)

    # direct assignment
    if expr[0] is 'number':
        cpi.assign(expr[1], lineno)
    elif expr[0] is 'id':
        cpi.assign(expr[1], lineno)
    # cpi should be erased if not direct assignment
    else:
        cpi.assign(None, lineno)

    for expr_str in func.csis:
        if lhs in func.csis[expr_str][-1].used_vars:
            func.csis[expr_str][-1].lines = [-1]


def update_optimization_information_with_increment(func, var_info, lineno):
    cpi = func.get_cpi(var_info[1])
    cpi.assign(None, lineno)


def remove_optimization_information_with_scope(func, scope, current_line):
    for var in scope.assigned_vars:
        func.cpis[var][-1].assign(None, current_line)


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


def get_cp_optimized_code(plain_code):
    new_code = list(plain_code)
    for (key, next_variable) in CP_DICT.items():
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


def get_cs_optimized_code(plain_code):
    target = sorted(CS_DICT.items(), key=lambda element: len(element[0]), reverse=True)
    new_code = list(plain_code)
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
