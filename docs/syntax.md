# Snake syntax and semantics

## Lexical rules

Source is UTF-8. Identifiers start with an ASCII letter or `_`, followed by letters, digits, or `_`; names are case-sensitive. Whitespace separates tokens. Newlines separate statements; semicolons are an alternate separator. `#` comments continue to the end of a line. Strings use single or double quotes and support `\n`, `\r`, `\t`, `\\`, `\"`, and `\'`. Numbers are decimal integers or decimal fractions (a fraction requires digits after the dot).

Keywords: `let`, `fixed`, `to`, `give`, `if`, `then`, `else`, `while`, `do`, `for`, `in`, `end`, `show`, `true`, `false`, `nil`, `and`, `or`, `not`, `global`, `break`, `continue`.

## Statements

```text
let name = expression
fixed name = expression
name = expression
show expression
to name(parameter, ...) do ... end
give [expression]
if expression then ... [else ...] end
while expression do ... end
for name in expression do ... end
global name [, name ...]
break
continue
```

Declarations are unique within their current scope. `fixed` names and function declarations cannot be reassigned. Assignment updates the nearest existing binding; it never implicitly declares a variable. Function calls have lexical closures. Function-local declarations live in the call frame; `global name` routes assignments to an already-declared root binding, even when shadowed locally. `give` exits the current function and supplies its result; falling off the end returns `nil`.

Branches and loop bodies have nested block scopes. A `for` loop accepts lists, strings, and ranges; its variable is local to each iteration. `break` and `continue` affect the innermost loop. Conditions accept any value: only `false` and `nil` are false-like.

## Expressions and precedence

From lowest to highest:

1. `or`
2. `and`
3. `==`, `!=`
4. `<`, `<=`, `>`, `>=`
5. `+`, `-`
6. `*`, `/`, `%`
7. unary `-`, `not`
8. calls, indexing (`items[0]`), and module members (`math.sqrt`)

Grouping uses parentheses. Lists use `[value, ...]`; trailing commas are permitted. `+` combines two numbers, strings, or lists. Other arithmetic operators require numbers. Division returns a number. Comparisons support two numbers or two strings; equality compares values without treating booleans as numbers. `and`/`or` short-circuit and return booleans. Indices are zero-based integers; negative indices follow sequence indexing.

`${name}` inside a string interpolates a visible variable. Interpolation accepts identifiers, not arbitrary expressions. A missing interpolation name is a name-resolution error.

## Types and conversions

Snake values are `integer`, `number` (floating point), `string`, `boolean`, `nil`, `list`, functions, and standard-library modules. There are no implicit string/number conversions. `str(value)`, `int(value)`, and `num(value)` perform explicit conversions. `int` truncates a number toward zero. A list can contain mixed values.

The lexer/parser/runtime report errors with source path, line, and column. Runtime resources are bounded by default to 100,000 execution steps per file invocation; statements and loop iterations consume steps. CLI `--limit 0` disables that limit. Recursive calls are additionally limited to 256 frames.
