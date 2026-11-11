from pathlib import Path
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken, UnexpectedCharacters
from sipl import ast

GRAMMAR_PATH = Path(__file__).parent.parent.parent / "grammar" / "sipl.lark"


@v_args(meta=True)
class SIPLTransformer(Transformer):
    def _span(self, meta) -> ast.SourceSpan:
        return ast.SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)

    def INT(self, token):
        return int(token.value)

    def VAR(self, token):
        return str(token.value)

    # Арифметичні вирази
    def num(self, meta, args):
        return ast.Num(span=self._span(meta), value=args[0])

    def var(self, meta, args):
        return ast.Var(span=self._span(meta), name=args[0])

    def add(self, meta, args):
        return ast.ABinOp(span=self._span(meta), op='+', left=args[0], right=args[1])

    def sub(self, meta, args):
        return ast.ABinOp(span=self._span(meta), op='-', left=args[0], right=args[1])

    def mult(self, meta, args):
        return ast.ABinOp(span=self._span(meta), op='*', left=args[0], right=args[1])

    # Логічні вирази
    def eq(self, meta, args):
        return ast.RelOp(span=self._span(meta), op='=', left=args[0], right=args[1])

    def gt(self, meta, args):
        return ast.RelOp(span=self._span(meta), op='>', left=args[0], right=args[1])

    def or_op(self, meta, args):
        return ast.LogicOp(span=self._span(meta), op='or', left=args[0], right=args[1])

    def neg_op(self, meta, args):
        return ast.NotOp(span=self._span(meta), expr=args[0])

    def skip_stmt(self, meta, args):
        return ast.Skip(span=self._span(meta))

    def assign_stmt(self, meta, args):
        return ast.Assign(span=self._span(meta), var_name=args[0], expr=args[1])

    def seq_stmt(self, meta, args):
        return ast.Seq(span=self._span(meta), stmt1=args[0], stmt2=args[1])

    def if_stmt(self, meta, args):
        return ast.If(span=self._span(meta), cond=args[0], then_branch=args[1], else_branch=args[2])

    def while_stmt(self, meta, args):
        return ast.While(span=self._span(meta), cond=args[0], body=args[1])

    def block_stmt(self, meta, args):
        return ast.Block(span=self._span(meta), stmt=args[0])

    def program(self, meta, args):
        return ast.Program(span=self._span(meta), stmt=args[0])


class SIPLSyntaxError(Exception):

    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Syntax Error at line {line}, column {column}: {message}")
        self.line = line
        self.column = column


def get_parser() -> Lark:
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar_content = f.read()
    return Lark(grammar_content, start="program", parser="lalr", propagate_positions=True)


def parse_sipl(code: str) -> ast.Program:
    parser = get_parser()
    try:
        raw_tree = parser.parse(code)
        ast_tree = SIPLTransformer().transform(raw_tree)
        return ast_tree
    except UnexpectedToken as e:
        expected = ", ".join(e.expected)
        msg = f"Unexpected token '{e.token.value}'. Expected one of: {expected}"
        raise SIPLSyntaxError(msg, e.line, e.column) from e
    except UnexpectedCharacters as e:
        msg = f"Unexpected character '{e.char}'"
        raise SIPLSyntaxError(msg, e.line, e.column) from e
    except Exception as e:
        if hasattr(e, 'line') and hasattr(e, 'column'):
            raise SIPLSyntaxError(str(e).split('\n')[0], getattr(e, 'line'), getattr(e, 'column')) from e
        raise e