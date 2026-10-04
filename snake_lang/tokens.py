"""Token definitions shared by the lexer and parser."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    literal: Any
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.kind} {self.lexeme!r} at {self.line}:{self.column}"
