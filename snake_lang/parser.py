"""Recursive-descent statement parser and precedence-climbing expression parser."""

from __future__ import annotations

from . import nodes as n
from .errors import ParseError
from .tokens import Token


class Parser:
    def __init__(self, tokens: list[Token], source: str = "<source>") -> None:
        self.tokens = tokens
        self.source = source
        self.current = 0
        self.loop_depth = 0
        self.function_depth = 0

    def parse(self) -> n.Program:
        statements: list[n.Node] = []
        self._skip_newlines()
        while not self._check("EOF"):
            statements.append(self._statement())
            if not self._check("EOF") and not self._check("NEWLINE") and not self._check("SEMICOLON"):
                raise self._error(self._peek(), "Expected a newline or ';' between statements.")
            self._skip_newlines()
        return n.Program(self._peek(), statements)

    def _statement(self) -> n.Node:
        if self._match("LET", "FIXED"):
            keyword = self._previous()
            name = self._consume("IDENTIFIER", "Expected a name after the declaration keyword.")
            self._consume("EQUAL", "Expected '=' after the declared name.")
            return n.Let(keyword, name, self._expression(), keyword.kind == "FIXED")
        if self._match("TO"):
            return self._function(self._previous())
        if self._match("IF"):
            return self._if(self._previous())
        if self._match("WHILE"):
            return self._while(self._previous())
        if self._match("FOR"):
            return self._for(self._previous())
        if self._match("SHOW"):
            token = self._previous()
            return n.Show(token, self._expression())
        if self._match("GIVE"):
            token = self._previous()
            if self.function_depth == 0:
                raise self._error(token, "'give' can only be used inside a function.")
            value = None if self._is_terminator() else self._expression()
            return n.Return(token, value)
        if self._match("GLOBAL"):
            token = self._previous()
            names = [self._consume("IDENTIFIER", "Expected a name after 'global'.")]
            while self._match("COMMA"):
                names.append(self._consume("IDENTIFIER", "Expected a name after ','."))
            return n.Global(token, names)
        if self._match("BREAK"):
            token = self._previous()
            if self.loop_depth == 0:
                raise self._error(token, "'break' can only be used inside a loop.")
            return n.Break(token)
        if self._match("CONTINUE"):
            token = self._previous()
            if self.loop_depth == 0:
                raise self._error(token, "'continue' can only be used inside a loop.")
            return n.Continue(token)
        if self._match("SEMICOLON"):
            return n.ExpressionStatement(self._previous(), n.Literal(self._previous(), None))
        if self._check("IDENTIFIER") and self._check_next("EQUAL"):
            name = self._advance()
            self._advance()
            return n.Assign(name, name, self._expression())
        token = self._peek()
        return n.ExpressionStatement(token, self._expression())

    def _function(self, token: Token) -> n.Function:
        name = self._consume("IDENTIFIER", "Expected a function name after 'to'.")
        self._consume("LEFT_PAREN", "Expected '(' after the function name.")
        parameters: list[Token] = []
        if not self._check("RIGHT_PAREN"):
            parameters.append(self._consume("IDENTIFIER", "Expected a parameter name."))
            while self._match("COMMA"):
                parameters.append(self._consume("IDENTIFIER", "Expected a parameter name."))
        if len({p.lexeme for p in parameters}) != len(parameters):
            raise self._error(name, "A parameter name cannot appear more than once.")
        self._consume("RIGHT_PAREN", "Expected ')' after parameters.")
        self._consume("DO", "Expected 'do' before the function body.")
        enclosing_loop_depth = self.loop_depth
        self.loop_depth = 0
        self.function_depth += 1
        try:
            body = self._block({"END"})
        finally:
            self.function_depth -= 1
            self.loop_depth = enclosing_loop_depth
        self._consume("END", "Expected 'end' after the function body.")
        return n.Function(token, name, parameters, body)

    def _if(self, token: Token) -> n.If:
        condition = self._expression()
        self._consume("THEN", "Expected 'then' after the condition.")
        then_branch = self._block({"ELSE", "END"})
        else_branch: list[n.Node] = []
        if self._match("ELSE"):
            else_branch = self._block({"END"})
        self._consume("END", "Expected 'end' after the conditional.")
        return n.If(token, condition, then_branch, else_branch)

    def _while(self, token: Token) -> n.While:
        condition = self._expression()
        self._consume("DO", "Expected 'do' after the loop condition.")
        self.loop_depth += 1
        body = self._block({"END"})
        self.loop_depth -= 1
        self._consume("END", "Expected 'end' after the loop body.")
        return n.While(token, condition, body)

    def _for(self, token: Token) -> n.For:
        name = self._consume("IDENTIFIER", "Expected a loop variable after 'for'.")
        self._consume("IN", "Expected 'in' after the loop variable.")
        iterable = self._expression()
        self._consume("DO", "Expected 'do' before the loop body.")
        self.loop_depth += 1
        body = self._block({"END"})
        self.loop_depth -= 1
        self._consume("END", "Expected 'end' after the loop body.")
        return n.For(token, name, iterable, body)

    def _block(self, terminators: set[str]) -> list[n.Node]:
        statements: list[n.Node] = []
        self._skip_newlines()
        while not self._check("EOF") and not self._check_any(terminators):
            statements.append(self._statement())
            if (not self._check("EOF") and not self._check("NEWLINE")
                    and not self._check("SEMICOLON") and not self._check_any(terminators)):
                raise self._error(self._peek(), "Expected a newline or ';' between statements.")
            self._skip_newlines()
        return statements

    def _expression(self) -> n.Node:
        return self._or()

    def _or(self) -> n.Node:
        expr = self._and()
        while self._match("OR"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._and())
        return expr

    def _and(self) -> n.Node:
        expr = self._equality()
        while self._match("AND"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._equality())
        return expr

    def _equality(self) -> n.Node:
        expr = self._comparison()
        while self._match("EQUAL_EQUAL", "BANG_EQUAL"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._comparison())
        return expr

    def _comparison(self) -> n.Node:
        expr = self._term()
        while self._match("LESS", "LESS_EQUAL", "GREATER", "GREATER_EQUAL"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._term())
        return expr

    def _term(self) -> n.Node:
        expr = self._factor()
        while self._match("PLUS", "MINUS"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._factor())
        return expr

    def _factor(self) -> n.Node:
        expr = self._unary()
        while self._match("STAR", "SLASH", "PERCENT"):
            op = self._previous()
            expr = n.Binary(op, expr, op, self._unary())
        return expr

    def _unary(self) -> n.Node:
        if self._match("MINUS", "NOT"):
            op = self._previous()
            return n.Unary(op, op, self._unary())
        return self._postfix()

    def _postfix(self) -> n.Node:
        expr = self._primary()
        while True:
            if self._match("LEFT_PAREN"):
                paren = self._previous()
                arguments: list[n.Node] = []
                if not self._check("RIGHT_PAREN"):
                    arguments.append(self._expression())
                    while self._match("COMMA"):
                        arguments.append(self._expression())
                self._consume("RIGHT_PAREN", "Expected ')' after arguments.")
                expr = n.Call(paren, expr, arguments)
            elif self._match("LEFT_BRACKET"):
                bracket = self._previous()
                index = self._expression()
                self._consume("RIGHT_BRACKET", "Expected ']' after the index.")
                expr = n.Index(bracket, expr, index)
            elif self._match("DOT"):
                dot = self._previous()
                name = self._consume("IDENTIFIER", "Expected a member name after '.'.")
                expr = n.Member(dot, expr, name.lexeme)
            else:
                return expr

    def _primary(self) -> n.Node:
        if self._match("FALSE"):
            return n.Literal(self._previous(), False)
        if self._match("TRUE"):
            return n.Literal(self._previous(), True)
        if self._match("NIL"):
            return n.Literal(self._previous(), None)
        if self._match("NUMBER", "STRING"):
            token = self._previous()
            return n.Literal(token, token.literal)
        if self._match("IDENTIFIER"):
            token = self._previous()
            return n.Variable(token, token.lexeme)
        if self._match("LEFT_PAREN"):
            expr = self._expression()
            self._consume("RIGHT_PAREN", "Expected ')' after the expression.")
            return expr
        if self._match("LEFT_BRACKET"):
            token = self._previous()
            items: list[n.Node] = []
            if not self._check("RIGHT_BRACKET"):
                items.append(self._expression())
                while self._match("COMMA"):
                    if self._check("RIGHT_BRACKET"):
                        break
                    items.append(self._expression())
            self._consume("RIGHT_BRACKET", "Expected ']' after the list.")
            return n.ListLiteral(token, items)
        raise self._error(self._peek(), "Expected an expression.", self._check("EOF"))

    def _is_terminator(self) -> bool:
        return self._check("NEWLINE") or self._check("SEMICOLON") or self._check("END") or self._check("ELSE") or self._check("EOF")

    def _skip_newlines(self) -> None:
        while self._match("NEWLINE", "SEMICOLON"):
            pass

    def _check_any(self, kinds: set[str]) -> bool:
        return any(self._check(kind) for kind in kinds)

    def _consume(self, kind: str, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        token = self._peek()
        incomplete = token.kind == "EOF"
        raise self._error(token, message, incomplete)

    def _match(self, *kinds: str) -> bool:
        if any(self._check(kind) for kind in kinds):
            self._advance()
            return True
        return False

    def _check(self, kind: str) -> bool:
        return self._peek().kind == kind

    def _check_next(self, kind: str) -> bool:
        return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].kind == kind

    def _advance(self) -> Token:
        if not self._check("EOF"):
            self.current += 1
        return self._previous()

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[max(0, self.current - 1)]

    def _error(self, token: Token, message: str, incomplete: bool = False) -> ParseError:
        return ParseError(message, self.source, token.line, token.column, incomplete)


def parse(tokens: list[Token], source: str = "<source>") -> n.Program:
    return Parser(tokens, source).parse()
