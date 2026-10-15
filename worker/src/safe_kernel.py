"""A small, stateless Python subset for public QuantLab teaching cells."""
from __future__ import annotations

import ast
import io
import math
import statistics
import operator

MAX_CELLS = 12
MAX_CELL_CHARS = 4_000
MAX_TOTAL_CHARS = 20_000
MAX_RANGE = 100
MAX_OUTPUT_CHARS = 12_000


class CellRejected(ValueError):
    """The submitted cell uses syntax outside the teaching subset."""


def _bounded_range(*args):
    values = range(*args)
    if len(values) > MAX_RANGE:
        raise CellRejected(f"range is limited to {MAX_RANGE} values")
    return values


def _safe_sqrt(value):
    if value < 0:
        raise ValueError("sqrt requires a non-negative number")
    return math.sqrt(value)


def _safe_mean(values):
    return statistics.mean(values)


def _safe_stdev(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _safe_sharpe(values, periods_per_year=252):
    deviation = _safe_stdev(values)
    return (statistics.mean(values) / deviation * _safe_sqrt(periods_per_year)) if deviation else 0.0


SAFE_BUILTINS = {
    "abs": abs,
    "bool": bool,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "max": max,
    "mean": _safe_mean,
    "min": min,
    "range": _bounded_range,
    "round": round,
    "sharpe": _safe_sharpe,
    "sqrt": _safe_sqrt,
    "stdev": _safe_stdev,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

def _bounded_value(value):
    if isinstance(value, (int, float)) and abs(value) > 1e100:
        raise CellRejected("Numeric values are limited to magnitude 1e100")
    if isinstance(value, (str, list, tuple, dict)) and len(value) > 1_000:
        raise CellRejected("Collections are limited to 1,000 items")
    return value


def _safe_binary(name, left, right):
    if name == "Add" and isinstance(left, (list, tuple, str)) and isinstance(right, type(left)):
        if len(left) + len(right) > 1_000:
            raise CellRejected("Collection growth is limited to 1,000 items")
    if name == "Mult":
        if isinstance(left, (list, tuple, str)) and isinstance(right, int):
            if len(left) * max(right, 0) > 1_000:
                raise CellRejected("Collection growth is limited to 1,000 items")
        elif isinstance(right, (list, tuple, str)) and isinstance(left, int):
            if len(right) * max(left, 0) > 1_000:
                raise CellRejected("Collection growth is limited to 1,000 items")
    operation = {
        "Add": operator.add,
        "Sub": operator.sub,
        "Mult": operator.mul,
        "Div": operator.truediv,
        "FloorDiv": operator.floordiv,
        "Mod": operator.mod,
        "Pow": operator.pow,
    }[name]
    result = operation(left, right)
    return _bounded_value(result)


class _BoundOperators(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        return ast.copy_location(
            ast.Call(
                func=ast.Name(id="__apply_binary", ctx=ast.Load()),
                args=[ast.Constant(type(node.op).__name__), node.left, node.right],
                keywords=[],
            ),
            node,
        )

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if not isinstance(node.target, ast.Name):
            raise CellRejected("Augmented assignment is limited to simple variables")
        return ast.copy_location(
            ast.Assign(
                targets=[node.target],
                value=ast.Call(
                    func=ast.Name(id="__apply_binary", ctx=ast.Load()),
                    args=[ast.Constant(type(node.op).__name__), ast.Name(id=node.target.id, ctx=ast.Load()), node.value],
                    keywords=[],
                ),
            ),
            node,
        )

ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.For, ast.If,
    ast.IfExp, ast.Name, ast.Load, ast.Store, ast.Constant, ast.List,
    ast.Tuple, ast.Dict, ast.Subscript, ast.Slice, ast.BinOp, ast.UnaryOp,
    ast.BoolOp, ast.Compare, ast.Call, ast.keyword, ast.ListComp,
    ast.comprehension, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.Pow, ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In,
    ast.NotIn, ast.Is, ast.IsNot,
)


def _validate_node(node: ast.AST) -> None:
    def check_loop_depth(current, depth=0):
        if isinstance(current, ast.For):
            depth += 1
            if depth > 2:
                raise CellRejected("Live cells may nest at most two bounded loops")
        for nested in ast.iter_child_nodes(current):
            check_loop_depth(nested, depth)

    check_loop_depth(node)
    for child in ast.walk(node):
        if not isinstance(child, ALLOWED_NODES):
            raise CellRejected(f"{type(child).__name__} is not available in live cells")
        if isinstance(child, ast.Name):
            if child.id.startswith("_"):
                raise CellRejected("Names beginning with underscore are unavailable")
            if isinstance(child.ctx, ast.Store) and child.id in SAFE_BUILTINS:
                raise CellRejected(f"Cannot assign to reserved helper {child.id!r}")
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Name) or child.func.id not in SAFE_BUILTINS and child.func.id != "print":
                raise CellRejected("Only documented research helpers may be called")
            if child.keywords:
                raise CellRejected("Keyword arguments are not available in live cells")
        if isinstance(child, ast.Pow):
            parent = next((p for p in ast.walk(node) if isinstance(p, ast.BinOp) and p.op is child), None)
            if parent is None or not isinstance(parent.right, ast.Constant) or not isinstance(parent.right.value, (int, float)) or abs(parent.right.value) > 8:
                raise CellRejected("Exponentiation requires a small numeric constant; use sqrt() for square roots")
        if isinstance(child, ast.For):
            if not isinstance(child.iter, ast.Call) or not isinstance(child.iter.func, ast.Name) or child.iter.func.id not in ("range", "enumerate", "zip"):
                raise CellRejected("Loops must iterate over range(), enumerate(), or zip()")
            if child.orelse:
                raise CellRejected("Loop else clauses are not available")
        if isinstance(child, ast.comprehension):
            if not isinstance(child.iter, ast.Call) or not isinstance(child.iter.func, ast.Name) or child.iter.func.id not in ("range", "enumerate", "zip"):
                raise CellRejected("Comprehensions must use range(), enumerate(), or zip()")
            if child.ifs:
                raise CellRejected("Filtered comprehensions are not available; use an explicit loop")
        if isinstance(child, ast.ListComp) and len(child.generators) != 1:
            raise CellRejected("List comprehensions may use one bounded iterator")


def _capture_print(output: io.StringIO):
    def print_limited(*values, sep=" ", end="\n"):
        text = sep.join(str(value) for value in values) + end
        if output.tell() + len(text) > MAX_OUTPUT_CHARS:
            raise CellRejected("Cell output exceeded the display limit")
        output.write(text)
    return print_limited


def execute_cells(cells):
    """Execute ordered cell source with a restricted namespace per request."""
    if not isinstance(cells, list) or not 1 <= len(cells) <= MAX_CELLS:
        raise CellRejected(f"Submit between 1 and {MAX_CELLS} cells")
    if any(not isinstance(cell, str) or len(cell) > MAX_CELL_CHARS for cell in cells):
        raise CellRejected(f"Each cell must be text no longer than {MAX_CELL_CHARS} characters")
    if sum(map(len, cells)) > MAX_TOTAL_CHARS:
        raise CellRejected(f"A page is limited to {MAX_TOTAL_CHARS} characters of code")

    namespace = {"__builtins__": SAFE_BUILTINS}
    outputs = []
    for source in cells:
        output = io.StringIO()
        namespace["print"] = _capture_print(output)
        try:
            tree = ast.parse(source, mode="exec")
            _validate_node(tree)
            tree = _BoundOperators().visit(tree)
            ast.fix_missing_locations(tree)
            namespace["__apply_binary"] = _safe_binary
            exec(compile(tree, "<quantlab-cell>", "exec"), namespace, namespace)
            rendered = output.getvalue()
            outputs.append({"ok": True, "output": rendered[:MAX_OUTPUT_CHARS]})
        except Exception as error:
            outputs.append({"ok": False, "output": f"{type(error).__name__}: {error}"[:1_000]})
            break
    return outputs
