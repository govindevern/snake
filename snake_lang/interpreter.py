"""Tree-walking Snake interpreter and execution environment."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import __version__
from . import nodes as n
from .environment import Environment
from .errors import (InvocationError, NameResolutionError, RuntimeErrorSnake,
                     TypeErrorSnake)
from .lexer import tokenize
from .parser import parse
from .tokens import Token


@dataclass
class NativeFunction:
    name: str
    callback: Callable[[list[Any]], Any]
    minimum: int
    maximum: int | None


@dataclass
class UserFunction:
    declaration: n.Function
    closure: Environment


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self, output: Callable[[str], None] = print,
                 input_fn: Callable[[str], str] = input,
                 max_steps: int | None = 100_000,
                 max_call_depth: int = 256,
                 file_root: str | Path | None = None) -> None:
        if max_steps is not None and max_steps < 1:
            raise ValueError("max_steps must be positive or None.")
        if max_call_depth < 1:
            raise ValueError("max_call_depth must be positive.")
        self.output = output
        self.input_fn = input_fn
        self.max_steps = max_steps
        self.max_call_depth = max_call_depth
        self.file_root = Path(file_root or Path.cwd()).resolve()
        self.steps = 0
        self.call_depth = 0
        self.source = "<source>"
        self.globals = Environment(source=self.source)
        self._install_builtins()

    def run(self, source_text: str, source: str = "<source>") -> Any:
        self.source = source
        self.globals.source = source
        self.steps = 0
        program = parse(tokenize(source_text, source), source)
        return self.execute(program, self.globals)

    def execute(self, statement: n.Node, environment: Environment) -> Any:
        self.steps += 1
        if self.max_steps is not None and self.steps > self.max_steps:
            self._runtime_error(statement.token, "Execution limit exceeded; possible infinite loop.")
        if isinstance(statement, n.Program):
            result = None
            for item in statement.statements:
                result = self.execute(item, environment)
            return result
        if isinstance(statement, n.Let):
            environment.define(statement.name.lexeme, self.evaluate(statement.initializer, environment),
                               statement.constant, statement.name)
            return None
        if isinstance(statement, n.Assign):
            environment.assign(statement.name, self.evaluate(statement.value, environment))
            return None
        if isinstance(statement, n.Show):
            self.output(self.stringify(self.evaluate(statement.expression, environment)))
            return None
        if isinstance(statement, n.ExpressionStatement):
            return self.evaluate(statement.expression, environment)
        if isinstance(statement, n.If):
            branch = statement.then_branch if self.truthy(self.evaluate(statement.condition, environment)) else statement.else_branch
            return self._execute_block(branch, Environment(environment))
        if isinstance(statement, n.While):
            result = None
            while self.truthy(self.evaluate(statement.condition, environment)):
                self.steps += 1
                if self.max_steps is not None and self.steps > self.max_steps:
                    self._runtime_error(statement.token, "Execution limit exceeded; possible infinite loop.")
                try:
                    result = self._execute_block(statement.body, Environment(environment))
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return result
        if isinstance(statement, n.For):
            iterable = self.evaluate(statement.iterable, environment)
            if not isinstance(iterable, (list, str, range)):
                self._type_error(statement.token, "'for' expects a list, string, or range.")
            result = None
            for value in iterable:
                self.steps += 1
                if self.max_steps is not None and self.steps > self.max_steps:
                    self._runtime_error(statement.token, "Execution limit exceeded; possible infinite loop.")
                loop_env = Environment(environment)
                loop_env.define(statement.name.lexeme, value)
                try:
                    result = self._execute_block(statement.body, loop_env)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return result
        if isinstance(statement, n.Function):
            environment.define(statement.name.lexeme, UserFunction(statement, environment),
                               constant=True, token=statement.name)
            return None
        if isinstance(statement, n.Return):
            value = None if statement.value is None else self.evaluate(statement.value, environment)
            raise _ReturnSignal(value)
        if isinstance(statement, n.Global):
            for name in statement.names:
                environment.mark_global(name)
            return None
        if isinstance(statement, n.Break):
            raise _BreakSignal()
        if isinstance(statement, n.Continue):
            raise _ContinueSignal()
        self._runtime_error(statement.token, f"Unsupported statement '{type(statement).__name__}'.")

    def evaluate(self, expression: n.Node, environment: Environment) -> Any:
        if isinstance(expression, n.Literal):
            if isinstance(expression.value, str):
                return self._interpolate(expression.value, environment, expression.token)
            return expression.value
        if isinstance(expression, n.Variable):
            return environment.get(Token("IDENTIFIER", expression.name, None,
                                         expression.token.line, expression.token.column))
        if isinstance(expression, n.ListLiteral):
            return [self.evaluate(item, environment) for item in expression.items]
        if isinstance(expression, n.Unary):
            right = self.evaluate(expression.right, environment)
            if expression.operator.kind == "NOT":
                return not self.truthy(right)
            self._require_number(right, expression.operator, "unary '-'")
            return -right
        if isinstance(expression, n.Binary):
            return self._evaluate_binary(expression, environment)
        if isinstance(expression, n.Call):
            callee = self.evaluate(expression.callee, environment)
            arguments = [self.evaluate(argument, environment) for argument in expression.arguments]
            return self._call(callee, arguments, expression.token)
        if isinstance(expression, n.Index):
            collection = self.evaluate(expression.collection, environment)
            index = self.evaluate(expression.index, environment)
            if not isinstance(collection, (list, str)):
                self._type_error(expression.token, "Only lists and strings can be indexed.")
            if type(index) is not int:
                self._type_error(expression.token, "An index must be an integer.")
            try:
                return collection[index]
            except IndexError:
                self._runtime_error(expression.token, f"Index {index} is out of range.")
        if isinstance(expression, n.Member):
            obj = self.evaluate(expression.object, environment)
            if not isinstance(obj, dict):
                self._runtime_error(expression.token, "Only standard-library modules have named members.")
            if expression.name not in obj:
                self._runtime_error(expression.token, f"Module has no member '{expression.name}'.")
            return obj[expression.name]
        self._runtime_error(expression.token, f"Unsupported expression '{type(expression).__name__}'.")

    def _evaluate_binary(self, expr: n.Binary, env: Environment) -> Any:
        op = expr.operator.kind
        left = self.evaluate(expr.left, env)
        if op == "AND":
            return self.truthy(left) and self.truthy(self.evaluate(expr.right, env))
        if op == "OR":
            return self.truthy(left) or self.truthy(self.evaluate(expr.right, env))
        right = self.evaluate(expr.right, env)
        if op == "EQUAL_EQUAL":
            return self._equal(left, right)
        if op == "BANG_EQUAL":
            return not self._equal(left, right)
        if op in ("LESS", "LESS_EQUAL", "GREATER", "GREATER_EQUAL"):
            if type(left) in (int, float) and type(right) in (int, float):
                pass
            elif type(left) is str and type(right) is str:
                pass
            else:
                self._type_error(expr.operator, "Comparison requires two numbers or two strings.")
            if op == "LESS":
                return left < right
            if op == "LESS_EQUAL":
                return left <= right
            if op == "GREATER":
                return left > right
            return left >= right
        if op == "PLUS":
            if type(left) in (int, float) and type(right) in (int, float):
                return left + right
            if type(left) is str and type(right) is str:
                return left + right
            if type(left) is list and type(right) is list:
                return left + right
            self._type_error(expr.operator, "'+' requires two numbers, two strings, or two lists.")
        self._require_number(left, expr.operator, "arithmetic")
        self._require_number(right, expr.operator, "arithmetic")
        if op == "MINUS":
            return left - right
        if op == "STAR":
            return left * right
        if op == "SLASH":
            if right == 0:
                self._runtime_error(expr.operator, "Division by zero.")
            return left / right
        if op == "PERCENT":
            if right == 0:
                self._runtime_error(expr.operator, "Remainder by zero.")
            return left % right
        self._runtime_error(expr.operator, f"Unknown operator '{expr.operator.lexeme}'.")

    def _call(self, callee: Any, arguments: list[Any], token: Token) -> Any:
        if isinstance(callee, NativeFunction):
            count = len(arguments)
            if count < callee.minimum or (callee.maximum is not None and count > callee.maximum):
                expected = str(callee.minimum) if callee.minimum == callee.maximum else (
                    f"{callee.minimum} or more" if callee.maximum is None else
                    f"{callee.minimum} to {callee.maximum}")
                label = "argument" if callee.minimum == callee.maximum == 1 else "arguments"
                raise InvocationError(f"{callee.name}() expects {expected} {label}, got {count}.",
                                      self.source, token.line, token.column)
            try:
                return callee.callback(arguments)
            except RuntimeErrorSnake:
                raise
            except (ValueError, TypeError, OverflowError) as error:
                raise TypeErrorSnake(f"{callee.name}(): {error}", self.source, token.line, token.column) from error
            except OSError as error:
                raise RuntimeErrorSnake(f"{callee.name}(): {error}", self.source, token.line, token.column) from error
            except IndexError as error:
                raise RuntimeErrorSnake(f"{callee.name}(): index is out of range.",
                                         self.source, token.line, token.column) from error
        if not isinstance(callee, UserFunction):
            raise InvocationError("This value is not callable.", self.source, token.line, token.column)
        declaration = callee.declaration
        if len(arguments) != len(declaration.parameters):
            label = "argument" if len(declaration.parameters) == 1 else "arguments"
            raise InvocationError(
                f"{declaration.name.lexeme}() expects {len(declaration.parameters)} {label}, got {len(arguments)}.",
                self.source, token.line, token.column)
        if self.call_depth >= self.max_call_depth:
            self._runtime_error(token, "Maximum function call depth exceeded.")
        frame = Environment(callee.closure)
        for parameter, value in zip(declaration.parameters, arguments):
            frame.define(parameter.lexeme, value)
        self.call_depth += 1
        try:
            self._execute_block(declaration.body, frame)
        except _ReturnSignal as signal:
            return signal.value
        finally:
            self.call_depth -= 1
        return None

    def _execute_block(self, statements: list[n.Node], environment: Environment) -> Any:
        result = None
        for statement in statements:
            result = self.execute(statement, environment)
        return result

    def _install_builtins(self) -> None:
        def native(name: str, callback: Callable[[list[Any]], Any],
                   minimum: int, maximum: int | None = -1) -> NativeFunction:
            return NativeFunction(name, callback, minimum, minimum if maximum == -1 else maximum)

        def number(value: Any, function: str) -> float | int:
            if type(value) not in (int, float):
                raise TypeError(f"{function} expects a number.")
            return value

        def integer(value: Any, function: str) -> int:
            if type(value) is not int:
                raise TypeError(f"{function} expects an integer.")
            return value

        def sequence(value: Any, function: str) -> list[Any]:
            if type(value) is not list:
                raise TypeError(f"{function} expects a list.")
            return value

        def text(value: Any, function: str) -> str:
            if type(value) is not str:
                raise TypeError(f"{function} expects a string.")
            return value

        core = {
            "len": native("len", lambda a: len(a[0]) if type(a[0]) in (list, str) else
                          (_ for _ in ()).throw(TypeError("len expects a list or string.")), 1),
            "str": native("str", lambda a: self.stringify(a[0]), 1),
            "int": native("int", lambda a: self._to_int(a[0]), 1),
            "num": native("num", lambda a: self._to_num(a[0]), 1),
            "type_of": native("type_of", lambda a: self._type_name(a[0]), 1),
            "range": native("range", lambda a: self._make_range(a), 1, 3),
            "input": native("input", lambda a: self.input_fn(self.stringify(a[0]) if a else ""), 0, 1),
            "output": native("output", lambda a: self._output(a), 1, None),
            "abs": native("abs", lambda a: abs(number(a[0], "abs")), 1),
            "min": native("min", lambda a: min(number(x, "min") for x in a), 1, None),
            "max": native("max", lambda a: max(number(x, "max") for x in a), 1, None),
            "round": native("round", lambda a: round(number(a[0], "round"), integer(a[1], "round") if len(a) > 1 else 0), 1, 2),
        }
        math_module = {
            "pi": math.pi, "e": math.e,
            "sqrt": native("math.sqrt", lambda a: math.sqrt(number(a[0], "sqrt")), 1),
            "floor": native("math.floor", lambda a: math.floor(number(a[0], "floor")), 1),
            "ceil": native("math.ceil", lambda a: math.ceil(number(a[0], "ceil")), 1),
            "sin": native("math.sin", lambda a: math.sin(number(a[0], "sin")), 1),
            "cos": native("math.cos", lambda a: math.cos(number(a[0], "cos")), 1),
            "log": native("math.log", lambda a: math.log(number(a[0], "log")), 1),
        }
        text_module = {
            "upper": native("text.upper", lambda a: text(a[0], "upper").upper(), 1),
            "lower": native("text.lower", lambda a: text(a[0], "lower").lower(), 1),
            "trim": native("text.trim", lambda a: text(a[0], "trim").strip(), 1),
            "split": native("text.split", lambda a: text(a[0], "split").split(text(a[1], "split") if len(a) > 1 else None), 1, 2),
            "join": native("text.join", lambda a: text(a[0], "join").join(text(item, "join") for item in sequence(a[1], "join")), 2),
            "contains": native("text.contains", lambda a: text(a[1], "contains") in text(a[0], "contains"), 2),
        }
        list_module = {
            "push": native("list.push", lambda a: (sequence(a[0], "push").append(a[1]), a[0])[1], 2),
            "pop": native("list.pop", lambda a: sequence(a[0], "pop").pop(integer(a[1], "pop")) if len(a) > 1 else sequence(a[0], "pop").pop(), 1, 2),
            "contains": native("list.contains", lambda a: any(self._equal(a[1], item)
                                                                 for item in sequence(a[0], "contains")), 2),
            "copy": native("list.copy", lambda a: sequence(a[0], "copy").copy(), 1),
        }
        io_module = {
            "read_line": core["input"],
            "write": core["output"],
        }

        def safe_path(value: Any) -> Path:
            name = text(value, "files")
            candidate = (self.file_root / name).resolve()
            try:
                candidate.relative_to(self.file_root)
            except ValueError as error:
                raise ValueError("file path must stay inside the program directory.") from error
            return candidate

        files_module = {
            "read": native("files.read", lambda a: safe_path(a[0]).read_text(encoding="utf-8"), 1),
            "write": native("files.write", lambda a: safe_path(a[0]).write_text(text(a[1], "files.write"), encoding="utf-8"), 2),
            "exists": native("files.exists", lambda a: safe_path(a[0]).is_file(), 1),
            "list": native("files.list", lambda a: sorted(p.name for p in safe_path(a[0] if a else ".").iterdir()), 0, 1),
        }
        system_module = {
            "version": __version__,
            "os_name": "Windows" if os.name == "nt" else "Unix",
            "cwd": str(self.file_root),
        }
        for name, value in core.items():
            self.globals.define(name, value, constant=True)
        for name, module in {
            "core": core, "math": math_module, "text": text_module, "list": list_module,
            "io": io_module, "files": files_module, "system": system_module,
        }.items():
            self.globals.define(name, module, constant=True)

    def _interpolate(self, value: str, env: Environment, token: Token) -> str:
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

        def replace(match: re.Match[str]) -> str:
            variable = Token("IDENTIFIER", match.group(1), None, token.line, token.column)
            return self.stringify(env.get(variable))
        return pattern.sub(replace, value)

    def stringify(self, value: Any) -> str:
        if value is None:
            return "nil"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, list):
            return "[" + ", ".join(self.stringify(item) for item in value) + "]"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def truthy(value: Any) -> bool:
        return value is not None and value is not False

    @staticmethod
    def _equal(left: Any, right: Any) -> bool:
        if type(left) in (int, float) and type(right) in (int, float):
            return left == right
        if type(left) is not type(right):
            return False
        if type(left) is list:
            return len(left) == len(right) and all(
                Interpreter._equal(a, b) for a, b in zip(left, right))
        if type(left) in (str, bool, type(None), range):
            return left == right
        return left is right

    def _require_number(self, value: Any, token: Token, operation: str) -> None:
        if type(value) not in (int, float):
            self._type_error(token, f"{operation} requires a number, got {self._type_name(value)}.")

    def _type_error(self, token: Token, message: str) -> None:
        raise TypeErrorSnake(message, self.source, token.line, token.column)

    def _runtime_error(self, token: Token, message: str) -> None:
        raise RuntimeErrorSnake(message, self.source, token.line, token.column)

    @staticmethod
    def _type_name(value: Any) -> str:
        if value is None:
            return "nil"
        if type(value) is bool:
            return "boolean"
        if type(value) is int:
            return "integer"
        if type(value) is float:
            return "number"
        if type(value) is str:
            return "string"
        if type(value) is list:
            return "list"
        if isinstance(value, (NativeFunction, UserFunction)):
            return "function"
        if type(value) is dict:
            return "module"
        return "value"

    def _to_int(self, value: Any) -> int:
        if type(value) is int:
            return value
        if type(value) is float:
            return int(value)
        if type(value) is str:
            return int(value.strip())
        raise TypeError("int expects a number or numeric string.")

    def _to_num(self, value: Any) -> int | float:
        if type(value) in (int, float):
            return value
        if type(value) is str:
            parsed = float(value.strip())
            return int(parsed) if parsed.is_integer() else parsed
        raise TypeError("num expects a number or numeric string.")

    def _make_range(self, args: list[Any]) -> range:
        values = [self._strict_int(arg, "range") for arg in args]
        if len(values) == 1:
            return range(values[0])
        if len(values) == 2:
            return range(values[0], values[1])
        return range(values[0], values[1], values[2])

    @staticmethod
    def _strict_int(value: Any, function: str) -> int:
        if type(value) is not int:
            raise TypeError(f"{function} expects integer arguments.")
        return value

    def _output(self, args: list[Any]) -> None:
        self.output(" ".join(self.stringify(value) for value in args))
        return None
