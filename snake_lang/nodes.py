"""Snake-specific abstract syntax tree node definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tokens import Token


@dataclass
class Node:
    token: Token


@dataclass
class Program(Node):
    statements: list[Node]


@dataclass
class Literal(Node):
    value: Any


@dataclass
class Variable(Node):
    name: str


@dataclass
class ListLiteral(Node):
    items: list[Node]


@dataclass
class Unary(Node):
    operator: Token
    right: Node


@dataclass
class Binary(Node):
    left: Node
    operator: Token
    right: Node


@dataclass
class Call(Node):
    callee: Node
    arguments: list[Node]


@dataclass
class Index(Node):
    collection: Node
    index: Node


@dataclass
class Member(Node):
    object: Node
    name: str


@dataclass
class Let(Node):
    name: Token
    initializer: Node
    constant: bool


@dataclass
class Assign(Node):
    name: Token
    value: Node


@dataclass
class Show(Node):
    expression: Node


@dataclass
class ExpressionStatement(Node):
    expression: Node


@dataclass
class If(Node):
    condition: Node
    then_branch: list[Node]
    else_branch: list[Node]


@dataclass
class While(Node):
    condition: Node
    body: list[Node]


@dataclass
class For(Node):
    name: Token
    iterable: Node
    body: list[Node]


@dataclass
class Function(Node):
    name: Token
    parameters: list[Token]
    body: list[Node]


@dataclass
class Return(Node):
    value: Node | None


@dataclass
class Global(Node):
    names: list[Token]


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass
