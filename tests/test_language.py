from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from snake_lang.cli import _repl, main
from snake_lang.errors import (InvocationError, LexError, NameResolutionError,
                               ParseError, RuntimeErrorSnake, TypeErrorSnake)
from snake_lang.interpreter import Interpreter
from snake_lang.lexer import tokenize
from snake_lang.parser import parse


class LexerTests(unittest.TestCase):
    def test_keywords_numbers_strings_and_locations(self) -> None:
        tokens = tokenize('let answer = 42\nshow "hi\\nthere" # comment\n')
        self.assertEqual([t.kind for t in tokens],
                         ["LET", "IDENTIFIER", "EQUAL", "NUMBER", "NEWLINE",
                          "SHOW", "STRING", "NEWLINE", "EOF"])
        self.assertEqual(tokens[3].literal, 42)
        self.assertEqual(tokens[5].line, 2)
        self.assertEqual(tokens[6].literal, "hi\nthere")

    def test_identifiers_and_numbers_are_ascii(self) -> None:
        with self.assertRaises(LexError):
            tokenize("let café = 1")
        with self.assertRaises(LexError):
            tokenize("let value = ١")

    def test_invalid_character_and_unterminated_string_have_locations(self) -> None:
        with self.assertRaisesRegex(LexError, r"sample\.snake:1:1"):
            tokenize("@", "sample.snake")
        with self.assertRaisesRegex(LexError, "Unterminated string"):
            tokenize('"unfinished')


class ParserTests(unittest.TestCase):
    def test_operator_precedence_builds_snake_nodes(self) -> None:
        program = parse(tokenize("show 1 + 2 * 3"))
        self.assertEqual(type(program).__name__, "Program")
        self.assertEqual(type(program.statements[0].expression).__name__, "Binary")
        self.assertEqual(type(program.statements[0].expression.right).__name__, "Binary")

    def test_statements_require_a_separator(self) -> None:
        with self.assertRaisesRegex(ParseError, "between statements"):
            parse(tokenize("let first = 1 let second = 2"))

    def test_missing_block_end_is_incomplete_input(self) -> None:
        with self.assertRaises(ParseError) as caught:
            parse(tokenize("if true then\n show 1"))
        self.assertTrue(caught.exception.incomplete)

    def test_incomplete_expression_is_marked_for_repl_continuation(self) -> None:
        with self.assertRaises(ParseError) as caught:
            parse(tokenize("show 1 +"))
        self.assertTrue(caught.exception.incomplete)

    def test_break_cannot_escape_into_a_function_from_an_outer_loop(self) -> None:
        with self.assertRaisesRegex(ParseError, "only be used inside a loop"):
            parse(tokenize("while true do\n to f() do\n  break\n end\nend"))


class InterpreterTests(unittest.TestCase):
    def run_snake(self, program: str, **options: object) -> tuple[Interpreter, list[str]]:
        lines: list[str] = []
        interpreter = Interpreter(output=lines.append, **options)
        interpreter.run(program, "test.snake")
        return interpreter, lines

    def test_types_operators_interpolation_and_lists(self) -> None:
        _, output = self.run_snake(
            'let count = 2\nlet values = [count, 3]\n'
            'list.push(values, 4)\n'
            'show "${count}:" + str(values[2]) + ":" + str(1 + 2 * 3)'
        )
        self.assertEqual(output, ["2:4:7"])

    def test_if_while_for_and_loop_control(self) -> None:
        _, output = self.run_snake(
            "let total = 0\nlet i = 0\n"
            "while i < 6 do\n"
            " i = i + 1\n"
            " if i == 2 then\n  continue\n end\n"
            " if i == 5 then\n  break\n end\n"
            " total = total + i\n"
            "end\n"
            "for value in range(3) do\n total = total + value\nend\n"
            "show total"
        )
        self.assertEqual(output, ["11"])

    def test_functions_recursion_scope_and_global_assignment(self) -> None:
        _, output = self.run_snake(
            "let counter = 1\n"
            "to factorial(n) do\n"
            " if n <= 1 then\n  give 1\n else\n  give n * factorial(n - 1)\n end\n"
            "end\n"
            "to increase() do\n global counter\n counter = counter + 1\n"
            " let local = 99\nend\n"
            "increase()\nshow factorial(5)\nshow counter"
        )
        self.assertEqual(output, ["120", "2"])

    def test_global_explicitly_bypasses_a_shadowing_local(self) -> None:
        _, output = self.run_snake(
            "let count = 1\n"
            "to update() do\n"
            " let count = 100\n"
            " global count\n"
            " count = count + 1\n"
            "end\n"
            "update()\nshow count"
        )
        self.assertEqual(output, ["2"])

    def test_constants_and_assignment_do_not_silently_fail(self) -> None:
        with self.assertRaisesRegex(RuntimeErrorSnake, "Cannot change constant"):
            self.run_snake("fixed rate = 2\nrate = 3")
        with self.assertRaises(NameResolutionError):
            self.run_snake("missing = 3")

    def test_list_equality_does_not_coerce_boolean_to_number(self) -> None:
        _, output = self.run_snake(
            "show [true] == [1]\nshow list.contains([true], 1)")
        self.assertEqual(output, ["false", "false"])

    def test_native_modules_and_input(self) -> None:
        _, output = self.run_snake(
            'let reply = io.read_line("name? ")\n'
            'show text.upper(reply)\nshow math.sqrt(81)\n'
            'show list.contains([1, 2], 2)',
            input_fn=lambda prompt: "snake",
        )
        self.assertEqual(output, ["SNAKE", "9", "true"])

    def test_system_module_reports_the_current_distribution_version(self) -> None:
        _, output = self.run_snake("show system.version")
        self.assertEqual(output, ["1.1.0"])

    def test_runtime_errors_are_snake_errors_with_locations(self) -> None:
        with self.assertRaisesRegex(TypeErrorSnake, r"test\.snake:1:10"):
            self.run_snake('show "a" - 1')
        with self.assertRaisesRegex(InvocationError, "expects 1 argument"):
            self.run_snake("len()")

    def test_execution_limit_stops_empty_infinite_loop(self) -> None:
        with self.assertRaisesRegex(RuntimeErrorSnake, "Execution limit exceeded"):
            self.run_snake("while true do\nend", max_steps=10)
        with self.assertRaisesRegex(RuntimeErrorSnake, "Execution limit exceeded"):
            self.run_snake("for i in range(1000000) do\nend", max_steps=10)

    def test_list_pop_out_of_range_is_reported_as_a_snake_error(self) -> None:
        with self.assertRaisesRegex(RuntimeErrorSnake, "index is out of range"):
            self.run_snake("list.pop([1], 4)")

    def test_file_module_is_confined_to_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Interpreter(output=lambda _: None, file_root=directory)
            interpreter.run('files.write("note.txt", "safe")\n'
                            'show files.read("note.txt")', "file.snake")
            self.assertEqual((Path(directory) / "note.txt").read_text(encoding="utf-8"), "safe")
            with self.assertRaisesRegex(RuntimeErrorSnake, "must stay inside"):
                interpreter.run('files.read("../outside.txt")', "file.snake")


class CliTests(unittest.TestCase):
    def test_version_and_check_commands(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("Snake 1.1.0", stdout.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.snake"
            path.write_text("show 1 + 2\n", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["check", str(path)]), 0)
            self.assertIn("OK:", stdout.getvalue())

            path.write_text("show )\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main(["check", str(path)]), 1)
            self.assertIn("valid.snake:1:", stderr.getvalue())

    def test_repl_accepts_multiline_function_definitions(self) -> None:
        stdout = io.StringIO()
        lines = ["to twice(n) do", " give n * 2", "end", "show twice(3)", ":quit"]
        with patch("builtins.input", side_effect=lines), redirect_stdout(stdout):
            self.assertEqual(_repl(), 0)
        self.assertIn("6", stdout.getvalue())
        self.assertIn("Snake 1.1.0", stdout.getvalue())

    def test_repl_recovers_from_invalid_input_and_exits_explicitly(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        lines = ["show )", ":exit"]
        with patch("builtins.input", side_effect=lines), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(_repl(), 0)
        self.assertIn("Expected an expression", stderr.getvalue())

    def test_cli_help_displays_supported_commands(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("run", stdout.getvalue())
        self.assertIn("check", stdout.getvalue())
        self.assertIn("repl", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
