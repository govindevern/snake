# Snake standard library

Standard functions are available directly and through `core`. Modules are values whose documented members are accessed with a dot. Invalid argument counts and invalid value types raise source-located Snake errors.

## Core

`len(list_or_string)`, `str(value)`, `int(value)`, `num(value)`, `type_of(value)`, `range(stop)`, `range(start, stop)`, `range(start, stop, step)`, `input([prompt])`, `output(value, ...)`, `abs(number)`, `min(number, ...)`, `max(number, ...)`, and `round(number[, places])`. `show expression` is the statement form for output. `core` exposes these functions.

## Modules

- `math`: constants `pi`, `e`; functions `sqrt`, `floor`, `ceil`, `sin`, `cos`, `log` (one numeric argument each).
- `text`: `upper(string)`, `lower(string)`, `trim(string)`, `split(string[, separator])`, `join(separator, list_of_strings)`, `contains(string, substring)`.
- `list`: `push(list, value)` (mutates and returns the list), `pop(list[, index])` (removes and returns an element), `contains(list, value)`, `copy(list)`.
- `io`: `read_line([prompt])`, `write(value, ...)`.
- `files`: `read(path)`, `write(path, string)`, `exists(path)`, `list([directory])`. Paths resolve under the executed `.snake` file's directory; the REPL uses its current working directory. Traversal outside that root is rejected.
- `system`: read-only `version`, `os_name`, and `cwd` values.

The initial V1.0 library intentionally excludes arbitrary command execution, network access, dynamic imports, and unrestricted filesystem access.
