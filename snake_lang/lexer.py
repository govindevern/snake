"""A hand-written lexer for Snake source files."""

from __future__ import annotations

from .errors import LexError
from .tokens import Token


KEYWORDS = {
    "let": "LET", "fixed": "FIXED", "to": "TO", "give": "GIVE",
    "if": "IF", "then": "THEN", "else": "ELSE", "while": "WHILE",
    "do": "DO", "for": "FOR", "in": "IN", "end": "END",
    "show": "SHOW", "true": "TRUE", "false": "FALSE", "nil": "NIL",
    "and": "AND", "or": "OR", "not": "NOT", "global": "GLOBAL",
    "break": "BREAK", "continue": "CONTINUE",
}


class Lexer:
    def __init__(self, text: str, source: str = "<source>") -> None:
        self.text = text
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1
        self.tokens: list[Token] = []

    def scan(self) -> list[Token]:
        while not self._at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token("EOF", "", None, self.line, self.column))
        return self.tokens

    def _scan_token(self) -> None:
        char = self._advance()
        singles = {
            "(": "LEFT_PAREN", ")": "RIGHT_PAREN", "[": "LEFT_BRACKET",
            "]": "RIGHT_BRACKET", ",": "COMMA", ".": "DOT", ";": "SEMICOLON",
            "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH",
            "%": "PERCENT",
        }
        if char in singles:
            self._add(singles[char])
        elif char == "=":
            self._add("EQUAL_EQUAL" if self._match("=") else "EQUAL")
        elif char == "!":
            if self._match("="):
                self._add("BANG_EQUAL")
            else:
                raise self._error("Use 'not' for logical negation; '!' is not an operator.")
        elif char in "<>":
            if self._match("="):
                self._add("LESS_EQUAL" if char == "<" else "GREATER_EQUAL")
            else:
                self._add("LESS" if char == "<" else "GREATER")
        elif char == "#":
            while self._peek() not in ("\n", "\0"):
                self._advance()
        elif char in " \t\r":
            return
        elif char == "\n":
            self._add("NEWLINE")
        elif char in "\"'":
            self._string(char)
        elif self._is_digit(char):
            self._number()
        elif self._is_alpha(char) or char == "_":
            self._identifier()
        else:
            raise self._error(f"Unexpected character {char!r}.")

    def _string(self, quote: str) -> None:
        chars: list[str] = []
        escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", "\"": "\"", "'": "'"}
        while not self._at_end() and self._peek() != quote:
            char = self._advance()
            if char == "\n":
                raise self._error("Strings cannot contain a literal newline.")
            if char == "\\":
                if self._at_end():
                    break
                escaped = self._advance()
                if escaped not in escapes:
                    raise self._error(f"Unknown string escape '\\{escaped}'.")
                chars.append(escapes[escaped])
            else:
                chars.append(char)
        if self._at_end():
            raise self._error("Unterminated string literal.")
        self._advance()
        self._add("STRING", "".join(chars))

    def _number(self) -> None:
        while self._is_digit(self._peek()):
            self._advance()
        is_float = False
        if self._peek() == "." and self._is_digit(self._peek_next()):
            is_float = True
            self._advance()
            while self._is_digit(self._peek()):
                self._advance()
        raw = self.text[self.start:self.current]
        self._add("NUMBER", float(raw) if is_float else int(raw))

    def _identifier(self) -> None:
        while self._is_alpha(self._peek()) or self._is_digit(self._peek()) or self._peek() == "_":
            self._advance()
        word = self.text[self.start:self.current]
        self._add(KEYWORDS.get(word, "IDENTIFIER"))

    def _add(self, kind: str, literal: object = None) -> None:
        self.tokens.append(Token(kind, self.text[self.start:self.current], literal,
                                 self.start_line, self.start_column))

    def _advance(self) -> str:
        char = self.text[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.text[self.current] != expected:
            return False
        self._advance()
        return True

    def _peek(self) -> str:
        return "\0" if self._at_end() else self.text[self.current]

    def _peek_next(self) -> str:
        return "\0" if self.current + 1 >= len(self.text) else self.text[self.current + 1]

    def _at_end(self) -> bool:
        return self.current >= len(self.text)

    @staticmethod
    def _is_alpha(char: str) -> bool:
        return "a" <= char <= "z" or "A" <= char <= "Z"

    @staticmethod
    def _is_digit(char: str) -> bool:
        return "0" <= char <= "9"

    def _error(self, message: str) -> LexError:
        return LexError(message, self.source, self.start_line, self.start_column)


def tokenize(text: str, source: str = "<source>") -> list[Token]:
    return Lexer(text, source).scan()
