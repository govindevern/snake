# Interpreter architecture

`lexer.py` turns source text into immutable, location-bearing `Token` values. `parser.py` implements recursive-descent statement parsing and a precedence-layered expression parser, producing only Snake node classes from `nodes.py`; it does not use Python's AST. `environment.py` provides nested bindings, constants, and explicit global assignment. `interpreter.py` evaluates those nodes directly, implements closures and control flow, and registers native functions and modules. `cli.py` provides file execution, syntax checking, and the REPL.

The public host entry point is `snake_lang.interpreter.Interpreter`. It accepts injected output/input callbacks, an execution-step budget, a recursion limit, and a filesystem root. `run(text, source)` lexes, parses, and executes using the interpreter's persistent global environment, which is useful for the REPL. Create a fresh `Interpreter` for an isolated program run.

No Snake source is passed to a Python compiler or evaluator. The runtime only exposes values and operations explicitly registered by Snake. Later bytecode work can preserve the lexer, grammar, AST, and standard-library contracts while replacing the tree-walking evaluator.
