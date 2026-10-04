"""Nested Snake variable environments with constant and global tracking."""

from __future__ import annotations

from typing import Any

from .errors import NameResolutionError, RuntimeErrorSnake
from .tokens import Token


class Environment:
    def __init__(self, parent: Environment | None = None, source: str | None = None) -> None:
        self.parent = parent
        self.source = source if source is not None else (parent.source if parent is not None else "<source>")
        self.values: dict[str, Any] = {}
        self.constants: set[str] = set()
        self.global_names: set[str] = set()

    def define(self, name: str, value: Any, constant: bool = False,
               token: Token | None = None) -> None:
        if name in self.values:
            raise RuntimeErrorSnake(f"'{name}' is already declared in this scope.", self.source,
                                    token.line if token else 1, token.column if token else 1)
        self.values[name] = value
        if constant:
            self.constants.add(name)

    def get(self, token: Token) -> Any:
        if token.lexeme in self.global_names:
            return self._root().values[token.lexeme]
        if token.lexeme in self.values:
            return self.values[token.lexeme]
        if self.parent is not None:
            return self.parent.get(token)
        raise NameResolutionError(f"Name '{token.lexeme}' is not defined.", self.source,
                                  line=token.line, column=token.column)

    def assign(self, token: Token, value: Any) -> None:
        name = token.lexeme
        if name in self.global_names:
            target = self._root()
            self._assign_here(target, token, value)
            return
        if name in self.values:
            self._assign_here(self, token, value)
            return
        if self.parent is not None and self.parent.contains(name):
            self.parent.assign(token, value)
            return
        raise NameResolutionError(f"Cannot assign to undefined name '{name}'. "
                                  "Declare it with 'let' first.",
                                  line=token.line, column=token.column)

    def mark_global(self, token: Token) -> None:
        if self.parent is None:
            if token.lexeme not in self.values:
                raise NameResolutionError(f"Global name '{token.lexeme}' is not defined.", self.source,
                                          line=token.line, column=token.column)
        elif not self._root().contains(token.lexeme):
            raise NameResolutionError(f"Global name '{token.lexeme}' is not defined.", self.source,
                                      line=token.line, column=token.column)
        self.global_names.add(token.lexeme)

    def contains(self, name: str) -> bool:
        return name in self.values or (self.parent is not None and self.parent.contains(name))

    def _root(self) -> Environment:
        env = self
        while env.parent is not None:
            env = env.parent
        return env

    @staticmethod
    def _assign_here(env: Environment, token: Token, value: Any) -> None:
        if token.lexeme not in env.values:
            raise NameResolutionError(f"Name '{token.lexeme}' is not defined.", env.source,
                                      line=token.line, column=token.column)
        if token.lexeme in env.constants:
            raise RuntimeErrorSnake(f"Cannot change constant '{token.lexeme}'.", env.source,
                                    line=token.line, column=token.column)
        env.values[token.lexeme] = value
