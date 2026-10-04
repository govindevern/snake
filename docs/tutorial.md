# Snake tutorial: functions and control flow

## Declare and update values

Use `let` for an assignable binding and `fixed` for a binding that cannot be reassigned:

```snake
let temperature = 18
temperature = temperature + 2
fixed greeting = "Good morning"
show "${greeting}; it is ${temperature} degrees."
```

Declarations belong to their current scope. Use `name = value` to update an existing binding; assignment does not create one implicitly.

## Choose a branch

Conditions end with `then`; each branch and loop ends with `end`:

```snake
let score = 72
if score >= 90 then
    show "excellent"
else
    if score >= 60 then
        show "passed"
    else
        show "try again"
    end
end
```

## Repeat work

Use `while` for a condition-controlled loop and `for` to visit a list, string, or `range`. `break` exits the nearest loop; `continue` skips to its next iteration.

```snake
let total = 0
for number in range(1, 6) do
    total = total + number
end
show total
```

## Define and call functions

Functions start with `to`, take parenthesized parameters, and return with `give`. Calls without an explicit `give` produce `nil`.

```snake
to square(number) do
    give number * number
end

show square(9)
```

Functions can call themselves. This recursive function is also provided as a runnable [example](../examples/fibonacci.snake):

```snake
to factorial(n) do
    if n <= 1 then
        give 1
    else
        give n * factorial(n - 1)
    end
end
show factorial(5)
```

Each function call has a local scope and captures the environment where its function was declared. Assignment updates the nearest existing binding. Use `global name` to bypass a nearer local binding and target an already-declared global:

```snake
let visits = 0
to visit() do
    let visits = 100
    global visits
    visits = visits + 1
end
```

## Read input and format output

`input([prompt])` returns a string. `show` prints one expression; `output(value, ...)` prints several values separated by spaces. `${name}` interpolation works for visible variable names:

```snake
let who = input("Your name? ")
show "Welcome, ${who}!"
```
