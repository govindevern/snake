# Snake errors

Errors use `source:line:column: message` format. The CLI writes errors to standard error and returns exit code 1; successful `check` and `run` commands return 0. Use `snake --debug run file.snake` (or `snake run file.snake --debug`) to include a Python traceback when diagnosing an interpreter implementation failure.

## Categories

- **Lexical error**: invalid source character, unsupported escape, or unterminated string.
- **Syntax error**: a token sequence does not follow the grammar, such as a missing `then`, `do`, or `end`.
- **Name-resolution error**: a name is not declared or a global assignment has no existing global binding.
- **Type error**: an operation or standard-library function receives an unsupported value type.
- **Invocation error**: a value is not callable or a call supplies the wrong number of arguments.
- **Runtime error**: valid syntax triggers an invalid operation, such as division by zero, reassignment of a constant, an out-of-range index, or an execution-limit violation.

## Diagnose and check

Run the syntax checker before execution:

```powershell
python -m snake_lang check .\examples\hello.snake
```

For example, `show missing` reports the missing identifier and its source location. `show 8 / 0` reports division by zero. Correct the source at the indicated position; runtime errors are not silently converted into `nil`. For an intentionally unbounded program, disable the step budget explicitly with `snake run file.snake --limit 0`.
