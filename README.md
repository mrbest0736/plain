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

## Download and install

You need Python 3.8 or newer. Nothing else — Plain has zero dependencies.

**Step 1. Get the code.** Every command below must run *inside the project
folder*, the one that contains `pyproject.toml`:

```bash
git clone https://github.com/mrbest0736/plain.git
cd plain
```

No git? On the GitHub page press the green **Code** button, choose
**Download ZIP**, unzip it, and open the unzipped folder.

**Step 2. Install the language:**

```bash
pip install .
```

On Windows you may see "Defaulting to user installation" — that is fine, it
installs for your user only. If the `plain` command is not found afterwards,
use `python -m plain` everywhere instead (it works identically).

**Step 3. Try it:**

```bash
plain run examples/hello.pln
```

Two errors people hit, and what they mean:

- `Neither 'setup.py' nor 'pyproject.toml' found` — you are not inside the
  project folder. `cd` into the folder that contains `pyproject.toml` first.
- `ENOENT ... plain-language-1.1.0.vsix` — the extension package is not in
  the folder you ran the command from. Build it first (next section), or give
  the full path to the file.

## CLI

```
plain run file.pln     Run a Plain program (compiled runner, see Performance).
plain run --tree file.pln
                       Run with the reference tree-walking interpreter.
plain check file.pln   Check the syntax without running it.
plain color file.pln   Print the program colour coded for the terminal.
plain repl             Interactive prompt (multi-line aware; type help inside it).
plain lsp              Run the language server for editors (VS Code, Cursor).
plain version          Print the version.
```

`python -m plain` works the same way as `plain`.

Every run is wrapped in safety limits, so a runaway program cannot eat your
machine. Tune or switch them off:

```
plain run file.pln --max-loop-rounds 1000000 --max-call-depth 500
plain run file.pln --max-output-chars 100000 --max-read-bytes 1000000
plain run file.pln --no-limits
```

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
| `security.pln` | AES-256 encrypt/decrypt, secure hash, secure random, wrong-key catch |

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

The easiest way: from the project folder, run the installer for your system —

```bat
.\install.bat      Windows
./install.sh       macOS and Linux
```

It installs the language, builds the extension package, and installs it into
VS Code and Cursor when it finds them.

Or by hand:

1. Build the package (pure Python zip, no Node toolchain needed):

```bash
python tools/package_vsix.py
```

This writes `dist/plain-language-1.1.0.vsix`. A ready-made copy is also
attached to every green run under **Actions** as the `plain-language-vsix`
artifact (sign in to GitHub to download artifacts).

2. Install it:

```bash
code --install-extension dist/plain-language-1.1.0.vsix
# Cursor:
cursor --install-extension dist/plain-language-1.1.0.vsix
```

or in the editor: Extensions view → `...` → **Install from VSIX...**

See [editors/plain-vscode/README.md](editors/plain-vscode/README.md).

## Security

Plain 1.1 takes Rust's lesson seriously: security is guarantees the language
enforces, not a library you can forget to call. Two layers:

**Built-in cryptography** (pure Python, no dependencies, in `plain/security.py`):

- `encrypt <message> with key <passphrase>.` — AES-256-CBC. The passphrase is
  stretched with PBKDF2-HMAC-SHA256 (100,000 rounds, 16-byte random salt), and
  the output is a base64 blob carrying its own salt and IV, so the same message
  never encrypts to the same text twice.
- `decrypt <blob> with key <passphrase>.` — reverses it. A wrong key or corrupted
  blob is a friendly catchable error, never a crash or silent garbage.
- `the secure hash of <text>` — SHA-256 fingerprint (always 64 characters).
- `secure random number from 1 to 6` — randomness from the operating system's
  cryptographically secure source (`secrets`), unlike the plain `random number`
  which is for games and simulations.

**Rust-style runtime guarantees** (on by default in both engines):

- Every list access is bounds-checked; out-of-range is a friendly error.
- Runaway loops are stopped after 10,000,000 total loop rounds.
- Runaway recursion is stopped at 200 calls deep.
- A program cannot print more than 10,000,000 characters.
- A single `wait` is capped at 60 seconds; a file read at 10,000,000 characters.
- File access is confined: `read file` / `write file` / `Use the file` can only
  open files inside the folder the program lives in — `../` escapes and absolute
  paths outside it are rejected.

All limits are adjustable with the `--max-*` flags and can be lifted with
`--no-limits`.

An honest note on the comparison with Rust: Rust's security is *memory safety*
enforced at compile time — it has no built-in encryption at all. Plain is
interpreted on CPython, so it cannot make the same compile-time guarantees;
what it does instead is make the safe path the only path at runtime (bounds
checks, limits, confinement are not optional) and ship real cryptography as
part of the language. The AES-256 implementation is pure Python, so it is
slower than a C-backed library — the trade for zero dependencies.

## Performance

Plain ships two engines with identical, test-verified behavior:

- **Reference interpreter** (`plain/interpreter.py`) — a readable
tree-walking evaluator.
- **Compiled runner** (`plain/vm.py`, the default) — compiles the AST once
into Python closures: no per-node dispatch, inlined type checks, fast-path
truthiness, and return-by-value instead of exceptions.

Measured with `python3 tools/bench.py` (CPython 3.12):

| Benchmark | Reference | Compiled | Speedup |
| --- | --- | --- | --- |
| fib(22) recursion | 0.211s | 0.069s | 3.0x |
| count loop 200k | 0.138s | 0.063s | 2.2x |
| math ops 100k | 0.280s | 0.085s | 3.3x |
| list ops 30k | 0.037s | 0.022s | 1.7x |
| text ops 50k | 0.069s | 0.044s | 1.6x |

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
  security.py     AES-256, PBKDF2, SHA-256, secure random, and the safety Limits.
  highlight.py    ANSI colour coder for the terminal (plain color).
  errors.py       Friendly error types that quote the offending line.
  lsp.py          Language server for editors (JSON-RPC over stdio).
  cli.py          run / check / color / repl / lsp / version.
editors/plain-vscode/  The VS Code / Cursor extension (grammar, snippets, LSP client).
dist/             The packaged extension, built by tools/package_vsix.py.
assets/           The Plain logo (logo.svg, icon.png).
tools/            make_logo.py, package_vsix.py, bench.py.
install.bat, install.sh   One-command installers (Windows; macOS/Linux).
tests/            pytest suite (lexer, parser, interpreter, VM parity, errors, examples, CLI, LSP).
examples/         16 runnable example programs.
LANGUAGE_GUIDE.md The complete language reference with the formal EBNF grammar.
```

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

The suite covers the lexer (including rejection of every forbidden symbol), the
parser, every statement type, error messages, all examples, and the CLI.
