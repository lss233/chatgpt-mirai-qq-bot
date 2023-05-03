import ast


class ExpressionChecker(ast.NodeVisitor):
    ALLOWED_NODES = (ast.Name, ast.Call, ast.Constant, ast.BoolOp, ast.Compare, ast.UnaryOp, ast.Expression, ast.boolop, ast.Subscript, ast.Load, ast.cmpop)

    def __init__(self, variables):
        self.variables = variables

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only function calls are allowed")

        allowed_funcs = {"int", "float", "bool", "len"}
        if node.func.id not in allowed_funcs:
            raise ValueError(f"Function {node.func.id} is not allowed")

    def generic_visit(self, node):
        if not isinstance(node, self.ALLOWED_NODES):
            raise ValueError(f"Node {node.__class__.__name__} is not allowed")

        super().generic_visit(node)


def evaluate_expression(expression, variables):
    parsed_expression = ast.parse(expression, mode="eval")

    checker = ExpressionChecker(variables)
    checker.visit(parsed_expression)
    try:
        return eval(compile(parsed_expression, '', mode="eval"), variables)
    except NameError:
        return False