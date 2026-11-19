from typing import Dict, Optional
from sipl import ast
from sipl.parser import parse_sipl


class SIPLRuntimeError(Exception):
    def __init__(self, message: str, span: Optional[ast.SourceSpan] = None):
        location = f" at line {span.line}, column {span.column}" if span else ""
        super().__init__(f"Runtime Error{location}: {message}")
        self.span = span


class UndefinedVariableError(SIPLRuntimeError):
    def __init__(self, var_name: str, span: Optional[ast.SourceSpan] = None):
        super().__init__(f"Variable '{var_name}' is not defined", span)
        self.var_name = var_name


class StepLimitExceededError(SIPLRuntimeError):
    def __init__(self, max_steps: int, span: Optional[ast.SourceSpan] = None):
        super().__init__(f"Execution step limit ({max_steps}) exceeded", span)
        self.max_steps = max_steps


class SIPLInterpreter:
    def __init__(self, max_steps: int = 10_000):
        if max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps
        self.steps = 0

    def execute(
        self,
        program: ast.Program,
        initial_state: Optional[Dict[str, int]] = None
    ) -> Dict[str, int]:
        self.steps = 0
        state: Dict[str, int] = dict(initial_state) if initial_state else {}
        self._eval_stm(program.stmt, state)
        return state

    def _tick(self, span: Optional[ast.SourceSpan]) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceededError(self.max_steps, span)

    def _eval_stm(self, stmt: ast.Stm, state: Dict[str, int]) -> None:
        self._tick(stmt.span)

        if isinstance(stmt, ast.Skip):
            return

        if isinstance(stmt, ast.Assign):
            val = self._eval_aexp(stmt.expr, state)
            state[stmt.var_name] = val
            return

        if isinstance(stmt, ast.Seq):
            self._eval_stm(stmt.stmt1, state)
            self._eval_stm(stmt.stmt2, state)
            return

        if isinstance(stmt, ast.Block):
            self._eval_stm(stmt.stmt, state)
            return

        if isinstance(stmt, ast.If):
            if self._eval_bexp(stmt.cond, state):
                self._eval_stm(stmt.then_branch, state)
            else:
                self._eval_stm(stmt.else_branch, state)
            return

        if isinstance(stmt, ast.While):
            while self._eval_bexp(stmt.cond, state):
                self._eval_stm(stmt.body, state)
                self._tick(stmt.span)
            return

        raise SIPLRuntimeError(f"Unknown statement node: {type(stmt).__name__}", stmt.span)

    def _eval_aexp(self, expr: ast.Aexp, state: Dict[str, int]) -> int:
        if isinstance(expr, ast.Num):
            return expr.value

        if isinstance(expr, ast.Var):
            if expr.name not in state:
                raise UndefinedVariableError(expr.name, expr.span)
            return state[expr.name]

        if isinstance(expr, ast.ABinOp):
            left = self._eval_aexp(expr.left, state)
            right = self._eval_aexp(expr.right, state)
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
            if expr.op == "*":
                return left * right
            raise SIPLRuntimeError(f"Unknown arithmetic operator '{expr.op}'", expr.span)

        raise SIPLRuntimeError(f"Unknown arithmetic node: {type(expr).__name__}", expr.span)

    def _eval_bexp(self, expr: ast.Bexp, state: Dict[str, int]) -> bool:
        if isinstance(expr, ast.RelOp):
            left = self._eval_aexp(expr.left, state)
            right = self._eval_aexp(expr.right, state)
            if expr.op == "=":
                return left == right
            if expr.op == ">":
                return left > right
            raise SIPLRuntimeError(f"Unknown relational operator '{expr.op}'", expr.span)

        if isinstance(expr, ast.LogicOp):
            if expr.op == "or":
                return self._eval_bexp(expr.left, state) or self._eval_bexp(expr.right, state)
            raise SIPLRuntimeError(f"Unknown logical operator '{expr.op}'", expr.span)

        if isinstance(expr, ast.NotOp):
            return not self._eval_bexp(expr.expr, state)

        raise SIPLRuntimeError(f"Unknown boolean node: {type(expr).__name__}", expr.span)


def run_sipl(
    code: str,
    initial_state: Optional[Dict[str, int]] = None,
    max_steps: int = 10_000
) -> Dict[str, int]:
    program = parse_sipl(code)
    interpreter = SIPLInterpreter(max_steps=max_steps)
    return interpreter.execute(program, initial_state)