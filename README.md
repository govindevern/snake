# Snake 1.1.0

Snake is an independent, general-purpose programming language. Its hand-written lexer, recursive-descent parser, Snake-specific AST, and tree-walking interpreter run Snake programs directly; source programs are not translated into Python. The Windows standalone distribution bundles the implementation runtime so end users do not need Python.

## Install on Windows

Download and run `Snake-Setup-1.1.0.exe`. Choose a system-wide installation (administrator permission) or a per-user installation when prompted. The installer adds its application folder to the matching PATH, preserves other entries, and offers an optional Start Menu shortcut. Open a **new** terminal after setup, then check:

```powershell
snake --version
snake --help
```

Windows 10/11 x64 is the initial standalone target. The installer and executable run offline after download. See [docs/installation.md](docs/installation.md) for setup, removal, and beginner instructions.

## Your first program

Create a file named `hello.snake` containing:

```snake
let name = input("What is your name? ")
show "Hello, ${name}!"
```

In PowerShell, from the folder where you saved the file:

```powershell
snake check .\hello.snake
snake run .\hello.snake
```

The `check` command checks syntax without running your program. Read the [beginner tutorial](docs/tutorial.md) to learn variables, conditions, loops, and functions.

## CLI

```text
snake --version
snake --help
snake run <file.snake> [--limit <steps>] [--debug]
snake check <file.snake>
snake repl
```

Source file paths may be relative to the current directory or absolute. The default interpreter step budget is 100,000; `snake run file.snake --limit 0` disables it. In the REPL, use `:quit` or `:exit` to leave. See [docs/errors.md](docs/errors.md) for diagnostics and troubleshooting.

## Language and library

Snake provides `let` variables, `fixed` constants, numbers, strings, booleans, lists, arithmetic and logic, nested `if` statements, `while`/`for` loops, scoped functions, return values, recursion, and input/output. Its standard library includes `core`, `math`, `text`, `list`, `io`, `files`, and `system`; documented filesystem operations are restricted to the program's directory. See [syntax](docs/syntax.md), [standard library](docs/stdlib.md), and [architecture](docs/architecture.md).

## Developer build

Build the Windows x64 standalone application with a 64-bit Python developer environment and PyInstaller:

```powershell
python -m pip install -e ".[build]"
python -m unittest discover -s tests -v
python build.py --format both --exe-only
```

The build runs the packaged CLI with Python-related environment variables removed and no Python directory on PATH. The one-file build is selected only if it passes the same smoke tests as the one-directory build; otherwise the tested one-directory bundle is staged. Build output is placed under `release\v1.1.0`.

To compile the offline installer as well, install Inno Setup 6 on the **build machine** and run:

```powershell
python build.py --format both
```

The installer compiler is not needed by Snake users. See [docs/building.md](docs/building.md) for exact build, test, verification, and installer requirements. An executable or installer is a release artifact only when that file exists and has passed the described checks.

Snake is distributed under the [MIT License](LICENSE).
