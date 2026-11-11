from dataclasses import dataclass
from typing import Optional

@dataclass
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int

@dataclass
class ASTNode:
    span: Optional[SourceSpan]

class Aexp(ASTNode):
    pass

@dataclass
class Num(Aexp):
    value: int

@dataclass
class Var(Aexp):
    name: str

@dataclass
class ABinOp(Aexp):
    op: str  # '+', '-', '*'
    left: Aexp
    right: Aexp

class Bexp(ASTNode):
    pass

@dataclass
class RelOp(Bexp):
    op: str  # '=', '>'
    left: Aexp
    right: Aexp

@dataclass
class LogicOp(Bexp):
    op: str  # 'or'
    left: Bexp
    right: Bexp

@dataclass
class NotOp(Bexp):
    expr: Bexp

class Stm(ASTNode):
    pass

@dataclass
class Skip(Stm):
    pass

@dataclass
class Assign(Stm):
    var_name: str
    expr: Aexp

@dataclass
class Seq(Stm):
    stmt1: Stm
    stmt2: Stm

@dataclass
class If(Stm):
    cond: Bexp
    then_branch: Stm
    else_branch: Stm

@dataclass
class While(Stm):
    cond: Bexp
    body: Stm

@dataclass
class Block(Stm):
    stmt: Stm

@dataclass
class Program(ASTNode):
    stmt: Stm