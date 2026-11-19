import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from sipl import ast
from sipl.parser import parse_sipl

EventType = Literal[
    "BeforeStatement",
    "AfterStatement",
    "VariableChange",
    "ConditionCheck",
    "Completed",
    "Error",
]

@dataclass
class TraceEvent:
    step: int
    event_type: EventType
    span: dict[str, int] | None = None
    data: dict[str, Any] = field(default_factory=dict)
    state: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SIPLRuntimeError(Exception):
    def __init__(self, message: str, span: ast.SourceSpan | None = None):
        location = f" at line {span.line}, column {span.column}" if span else ""
        super().__init__(f"Runtime Error{location}: {message}")
        self.span = span


class UndefinedVariableError(SIPLRuntimeError):
    def __init__(self, var_name: str, span: ast.SourceSpan | None = None):
        super().__init__(f"Variable '{var_name}' is not defined", span)
        self.var_name = var_name


class StepLimitExceededError(SIPLRuntimeError):
    def __init__(self, max_steps: int, span: ast.SourceSpan | None = None):
        super().__init__(f"Execution step limit ({max_steps}) exceeded", span)
        self.max_steps = max_steps


class SIPLInterpreter:
    def __init__(self, max_steps: int = 10_000):
        if max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps
        self.steps = 0
        self.trace: list[TraceEvent] = []

    @staticmethod
    def _format_span(span: ast.SourceSpan | None) -> dict[str, int] | None:
        if span is None:
            return None
        return {
            "line": span.line,
            "column": span.column,
            "end_line": span.end_line,
            "end_column": span.end_column,
        }

    def _record(
        self,
        event_type: EventType,
        span: ast.SourceSpan | None,
        state: dict[str, int],
        **data: Any,
    ) -> None:
        self.trace.append(
            TraceEvent(
                step=self.steps,
                event_type=event_type,
                span=self._format_span(span),
                data=data,
                state=dict(state),
            )
        )

    def execute(
        self,
        program: ast.Program,
        initial_state: dict[str, int] | None = None
    ) -> dict[str, int]:
        self.steps = 0
        self.trace = []
        state: dict[str, int] = dict(initial_state) if initial_state else {}

        try:
            self._eval_stm(program.stmt, state)
        except SIPLRuntimeError as exc:
            self._record(
                "Error",
                exc.span,
                state,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise

        self._record("Completed", program.span, state, total_steps=self.steps)
        return state

    def trace_to_json(self, indent: int | None = 2) -> str:
        return json.dumps([event.to_dict() for event in self.trace], indent=indent)

    def _tick(self, span: ast.SourceSpan | None) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceededError(self.max_steps, span)

    def _eval_stm(self, stmt: ast.Stm, state: dict[str, int]) -> None:
        self._tick(stmt.span)
        stmt_type = type(stmt).__name__
        self._record("BeforeStatement", stmt.span, state, stmt_type=stmt_type)

        if isinstance(stmt, ast.Skip):
            pass
        elif isinstance(stmt, ast.Assign):
            val = self._eval_aexp(stmt.expr, state)
            old_val = state.get(stmt.var_name)
            state[stmt.var_name] = val
            self._record(
                "VariableChange",
                stmt.span,
                state,
                var_name=stmt.var_name,
                old_value=old_val,
                new_value=val,
            )
        elif isinstance(stmt, ast.Seq):
            self._eval_stm(stmt.stmt1, state)
            self._eval_stm(stmt.stmt2, state)
        elif isinstance(stmt, ast.Block):
            self._eval_stm(stmt.stmt, state)
        elif isinstance(stmt, ast.If):
            if self._eval_bexp(stmt.cond, state):
                self._eval_stm(stmt.then_branch, state)
            else:
                self._eval_stm(stmt.else_branch, state)
        elif isinstance(stmt, ast.While):
            while self._eval_bexp(stmt.cond, state):
                self._eval_stm(stmt.body, state)
                self._tick(stmt.span)
        else:
            raise SIPLRuntimeError(f"Unknown statement node: {stmt_type}", stmt.span)

        self._record("AfterStatement", stmt.span, state, stmt_type=stmt_type)

    def _eval_aexp(self, expr: ast.Aexp, state: dict[str, int]) -> int:
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

    def _eval_bexp(self, expr: ast.Bexp, state: dict[str, int]) -> bool:
        result: bool
        if isinstance(expr, ast.RelOp):
            left = self._eval_aexp(expr.left, state)
            right = self._eval_aexp(expr.right, state)
            if expr.op == "=":
                result = left == right
            elif expr.op == ">":
                result = left > right
            else:
                raise SIPLRuntimeError(f"Unknown relational operator '{expr.op}'", expr.span)
        elif isinstance(expr, ast.LogicOp):
            if expr.op == "or":
                result = self._eval_bexp(expr.left, state) or self._eval_bexp(expr.right, state)
            else:
                raise SIPLRuntimeError(f"Unknown logical operator '{expr.op}'", expr.span)
        elif isinstance(expr, ast.NotOp):
            result = not self._eval_bexp(expr.expr, state)
        else:
            raise SIPLRuntimeError(f"Unknown boolean node: {type(expr).__name__}", expr.span)

        self._record(
            "ConditionCheck",
            expr.span,
            state,
            expr_type=type(expr).__name__,
            result=result,
        )
        return result


def run_sipl(
    code: str,
    initial_state: dict[str, int] | None = None,
    max_steps: int = 10_000,
) -> dict[str, int]:
    program = parse_sipl(code)
    interpreter = SIPLInterpreter(max_steps=max_steps)
    return interpreter.execute(program, initial_state)

def trace_sipl(
    code: str,
    initial_state: dict[str, int] | None = None,
    max_steps: int = 10_000,
) -> list[TraceEvent]:
    program = parse_sipl(code)
    interpreter = SIPLInterpreter(max_steps=max_steps)
    interpreter.execute(program, initial_state)
    return interpreter.trace


def trace_sipl_json(
    code: str,
    initial_state: dict[str, int] | None = None,
    max_steps: int = 10_000,
    indent: int | None = 2,
) -> str:
    program = parse_sipl(code)
    interpreter = SIPLInterpreter(max_steps=max_steps)
    interpreter.execute(program, initial_state)
    return interpreter.trace_to_json(indent=indent)