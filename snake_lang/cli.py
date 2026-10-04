"""Command-line interface for running and checking Snake programs."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from . import __version__
from .errors import SnakeError
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import parse


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="snake", description="Run programs in the Snake language.")
    parser.add_argument("--version", action="version", version=f"Snake {__version__}")
    parser.add_argument("--debug", action="store_true", help="show Python tracebacks for interpreter bugs")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run", help="run a .snake source file")
    run.add_argument("--debug", action="store_true", default=argparse.SUPPRESS,
                     help="show Python tracebacks for interpreter bugs")
    run.add_argument("file", type=Path)
    run.add_argument("--limit", type=int, default=100_000,
                     help="maximum execution steps (default: 100000; 0 disables the limit)")
    check = commands.add_parser("check", help="check a .snake file without running it")
    check.add_argument("--debug", action="store_true", default=argparse.SUPPRESS,
                       help="show Python tracebacks for interpreter bugs")
    check.add_argument("file", type=Path)
    repl = commands.add_parser("repl", help="start the interactive interpreter")
    repl.add_argument("--debug", action="store_true", default=argparse.SUPPRESS,
                      help="show Python tracebacks for interpreter bugs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "repl":
        return _repl(args.debug)
    file_path = args.file.resolve()
    try:
        source_text = file_path.read_text(encoding="utf-8")
        if args.command == "check":
            parse(tokenize(source_text, str(file_path)), str(file_path))
            print(f"OK: {file_path}")
            return 0
        limit = None if args.limit == 0 else args.limit
        Interpreter(max_steps=limit, file_root=file_path.parent).run(source_text, str(file_path))
        return 0
    except (SnakeError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1


def _repl(debug: bool = False) -> int:
    interpreter = Interpreter()
    pending: list[str] = []
    print(f"Snake {__version__} interactive interpreter. Type :quit or :exit to leave.")
    while True:
        prompt = "... " if pending else "snake> "
        try:
            line = input(prompt)
        except EOFError:
            if pending:
                print("Incomplete input discarded.", file=sys.stderr)
            print()
            return 0
        except KeyboardInterrupt:
            pending.clear()
            print("\nInput cancelled.")
            continue
        if not pending and line.strip() in (":quit", ":exit"):
            return 0
        pending.append(line)
        text = "\n".join(pending)
        try:
            result = interpreter.run(text, "<repl>")
        except SnakeError as error:
            if getattr(error, "incomplete", False):
                continue
            print(error, file=sys.stderr)
            if debug:
                traceback.print_exc()
        except KeyboardInterrupt:
            print("\nExecution interrupted.", file=sys.stderr)
        else:
            if result is not None:
                print(interpreter.stringify(result))
        pending.clear()


if __name__ == "__main__":
    raise SystemExit(main())
