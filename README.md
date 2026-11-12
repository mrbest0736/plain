# Plain

![Plain logo](assets/icon.png)

Plain is a small programming language written almost entirely in English words,
so that someone with no programming background can read and write software.

The one hard rule: **the only punctuation allowed in Plain source code is the
comma and the period.** Everything else is spelled out as words. If you type a
forbidden symbol, the interpreter tells you, in a friendly sentence, which line
it was on and which word to use instead.

```
Note a tiny Plain program end note.
Set name to text Ada end text.
Set score to 10.
Change score by 5.
If score is greater than 10, then
  Say text Hello, end text, name, text your score is end text, score.
otherwise
  Say text Keep trying. end text
end if.
```

## Quickstart

You need Python 3.8 or newer. No other dependencies.

```bash
cd plain-language
python -m plain run examples/hello.pln
```

Optionally install the `plain` command:

```bash
pip install .
plain run examples/hello.pln
```

## CLI

```
plain run file.pln     Run a Plain program (compiled runner, see Performance).
plain run --tree file.pln
                       Run with the reference tree-walking interpreter.
plain check file.pln   Check the syntax without running it.
plain repl             Interactive prompt (multi-line aware; type help inside it).
plain lsp              Run the language server for editors (VS Code, Cursor).
plain version          Print the version.
```

`python -m plain` works the same way as `plain`.

## The language in one minute

- Every statement ends with a period. Commas separate items and clauses.
- Keywords and names are case-insensitive. Names can be several words: `total score`.
- Text literals: `text Hello, world. end text` (anything may appear inside).
- Numbers: `42`, `3 point 14`, `negative 5`. Truth values: `yes`, `no`. Empty: `nothing`.
- Comments: `Note this explains the code end note.`
- Blocks close with explicit words: `end if.`, `end loop.`, `end function.` No indentation rules.
- Math with words: `plus`, `minus`, `times`, `divided by`, `remainder of`,
  `to the power of`, `the square root of`, `the absolute value of`, `rounded`,
  `the larger of x and y`, `the smaller of x and y`. Use `group ... end group` to force order.
- Lists start at item 1: `Make a list called scores holding 5, 10, 15.`

A taste of each feature:

```
Set total to 0.
Repeat 10 times,
  Change total by 1.
end loop.

While total is greater than 0,
  Change total by negative 1.
end loop.

For each thing in my list,
  Say thing.
end loop.

Count from 1 to 10 using i by 2,
  Say i.
end loop.

To add numbers with first and second, do
  give back first plus second.
end function.

Set answer to the result of add numbers with 3 and 4.

Try,
  Say item 99 of my list.
if something goes wrong,
  Say text Oops: end text, the problem.
end try.
```

The full reference, including the formal grammar, is in
[LANGUAGE_GUIDE.md](LANGUAGE_GUIDE.md).

## Examples

All examples in `examples/` run and are exercised by the test suite:

| File | Shows |
| --- | --- |
| `hello.pln` | Say, Write, text literals |
| `fizzbuzz.pln` | Count loop, remainder of, if/otherwise if |
| `factorial.pln` | Recursion, functions |
| `fibonacci.pln` | Functions, loops, lists |
| `primes.pln` | Nested loops, stop the loop |
| `todo.pln` | Lists, Ask, remove, sort |
| `temperature.pln` | Math, Ask the user for a number |
| `wordcount.pln` | split, the length of, contains |
| `calculator.pln` | Ask, group, try/catch |
| `guessing.pln` | The spec's guessing game, verbatim |
| `lists.pln` | Every list operation |
| `functions.pln` | Parameters, give back, closures |
| `errors.pln` | try/catch, the problem |
| `helpers.pln`, `import_demo.pln` | Use the file imports |

Run any of them:

```bash
python -m plain run examples/fizzbuzz.pln
echo 7 | python -m plain run examples/guessing.pln
```

## Use it in VS Code or Cursor

The `editors/plain-vscode/` folder is a complete editor extension: syntax
highlighting, 16 snippets, a `.pln` file icon, `Plain: Run File` /
`Plain: Check File` commands, and **live friendly diagnostics** (the same
plain-English errors, as squiggles while you type) via a built-in language
server (`plain lsp`, no external dependencies).

An installable package is included: **`dist/plain-language-1.0.0.vsix`**.

1. Install the language: `pip install .` (from this folder)
2. Install the extension:

```bash
code --install-extension dist/plain-language-1.0.0.vsix
# Cursor:
cursor --install-extension dist/plain-language-1.0.0.vsix
```

or in the editor: Extensions view → `...` → **Install from VSIX...**

Rebuild the package any time with `python3 tools/package_vsix.py` (pure
Python zip, no Node toolchain needed). See
[editors/plain-vscode/README.md](editors/plain-vscode/README.md).

## Performance

Plain 1.0 ships two engines with identical, test-verified behavior:

- **Reference interpreter** (`plain/interpreter.py`) — a readable
tree-walking evaluator.
- **Compiled runner** (`plain/vm.py`, the default) — compiles the AST once
into Python closures: no per-node dispatch, inlined type checks, fast-path
truthiness, and return-by-value instead of exceptions.

Measured with `python3 tools/bench.py` (CPython 3.12):

| Benchmark | Reference | Compiled | Speedup |
| --- | --- | --- | --- |
| fib(22) recursion | 0.210s | 0.068s | 3.1x |
| count loop 200k | 0.121s | 0.052s | 2.3x |
| math ops 100k | 0.260s | 0.076s | 3.4x |
| list ops 30k | 0.033s | 0.020s | 1.7x |
| text ops 50k | 0.061s | 0.038s | 1.6x |

An honest note: Plain is a teaching language hosted on CPython, so the same
`fib(22)` written directly in Python 3 runs in about 0.0014s — roughly 50x
faster than Plain's compiled runner — and compiled languages like C or Rust
are faster still. No interpreter written in Python can outrun the runtime
that interprets it. What the compiled runner buys is wasting as little of the
host runtime as possible; a version 2 bytecode compiler (or a native
backend) is the next step for real speed.

## Project layout

```
plain/
  lexer.py        Words, numbers, text literals, commas, periods. Rejects symbols.
  ast_nodes.py    The AST node classes (one per statement and expression kind).
  parser.py       Recursive-descent parser following the grammar in the guide.
  interpreter.py  Reference tree-walking evaluator: scopes, loops, functions, errors.
  vm.py           The compiled fast runner (default engine), verified against the reference.
  builtins.py     Value helpers and built-in operations (random, time, files...).
  errors.py       Friendly error types that quote the offending line.
  lsp.py          Language server for editors (JSON-RPC over stdio).
  cli.py          run / check / repl / lsp / version.
editors/plain-vscode/  The VS Code / Cursor extension (grammar, snippets, LSP client).
dist/             The packaged extension: plain-language-1.0.0.vsix
assets/           The Plain logo (logo.svg, icon.png).
tools/            make_logo.py, package_vsix.py, bench.py.
tests/            pytest suite (lexer, parser, interpreter, VM parity, errors, examples, CLI, LSP).
examples/         15 runnable example programs.
LANGUAGE_GUIDE.md The complete language reference with the formal EBNF grammar.
```

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

The suite covers the lexer (including rejection of every forbidden symbol), the
parser, every statement type, error messages, all examples, and the CLI.
