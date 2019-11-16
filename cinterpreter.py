from cyacc import lexer, parser

f = open("inputs/input0.c", "r")
code = "".join(f.readlines())
f.close()

tree = parser.parse(code, lexer=lexer)
print(tree)