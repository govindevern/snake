"""Source-aware errors raised by Snake's language engine."""


class SnakeError(Exception):
    def __init__(self, message: str, source: str = "<source>", line: int = 1, column: int = 1) -> None:
        self.message = message
        self.source = source
        self.line = line
        self.column = column
        super().__init__(self.format())

    def format(self) -> str:
        return f"{self.source}:{self.line}:{self.column}: {self.message}"


class LexError(SnakeError):
    """Invalid character or literal in source."""


class ParseError(SnakeError):
    """Source does not match the Snake grammar."""

    def __init__(self, message: str, source: str = "<source>", line: int = 1, column: int = 1,
                 incomplete: bool = False) -> None:
        self.incomplete = incomplete
        super().__init__(message, source, line, column)


class RuntimeErrorSnake(SnakeError):
    """An error while evaluating valid Snake code."""


class NameResolutionError(RuntimeErrorSnake):
    """A name is not defined in the active environment."""


class TypeErrorSnake(RuntimeErrorSnake):
    """An operation received values of unsupported types."""


class InvocationError(RuntimeErrorSnake):
    """A function call has an invalid argument list."""
