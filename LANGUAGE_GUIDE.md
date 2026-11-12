# The Plain Language Guide

Plain is a programming language written almost entirely in English words. This
guide is the complete reference: the rules, every statement and expression, the
formal grammar, and the deliberate decisions made where phrasings could
conflict.

## 1. The one hard rule

**The only punctuation symbols allowed in Plain source code are the comma and
the period.**

Letters, digits and spaces are allowed. Digits may only appear inside number
literals. Everything that other languages write with symbols is spelled out as
words: `+` becomes `plus`, `(` becomes `group`, `=` becomes `is equal to` (or
`to`, when setting a variable), and so on.

If you type a forbidden symbol, the interpreter refuses politely and tells you
what to write instead:

```
I found a syntax problem on line 4 of the Plain program:
    Set total to 3 + 4.
I found a plus sign on line 4. Use the word plus instead.
```

## 2. Basic rules

- Every statement ends with a period.
- Commas separate items and clauses. They are required between the items of a
  `Say`, a list, or a function call; elsewhere they are optional and ignored.
- Keywords and names are case-insensitive. `SET SCORE TO 10.` and
  `set score to 10.` are the same statement.
- A name is one or more words: `score`, `total score`, `name of the player`.
- Blocks are closed with explicit end words — `end if.`, `end loop.`,
  `end function.`, `end try.` — so indentation is purely for humans.
- Comments run from the word `Note` to the words `end note.`. Inside a note any
  characters are allowed, except the words `end note`.

## 3. Values

| Kind | Written as | Examples |
| --- | --- | --- |
| Whole number | digits | `42`, `0`, `7` |
| Decimal | digits, the word `point`, digits | `3 point 14` |
| Negative | the word `negative` before a number | `negative 5` |
| Text | between `text` and `end text` | `text Hello, world. end text` |
| Truth value | `yes` or `no` | `yes` |
| Empty value | `nothing` | `nothing` |
| List | `a list holding ...` | `a list holding 1, 2, 3` |

Typing is dynamic: a variable can hold any kind of value, and lists may mix
kinds, including other lists. There is no difference between whole numbers and
decimals when counting; `divided by` always produces a decimal answer when the
division is not exact.

## 4. Keyword table

These 62 words are **reserved**. They cannot appear inside a name. That is what
makes multi-word names unambiguous: the parser always knows where a name ends.

**Statements:** set, change, say, write, ask, make, remove, sort, reverse, run,
try, use, wait, give, back, stop, skip

**Control flow:** if, then, otherwise, end, while, repeat, for, each, in, from,
using, function, do, loop, times, note

**Phrase words:** the, a, of, to, by, with, holding, called, item

**Literals and prefixes:** text, group, yes, no, nothing, not, negative

**Operators:** and, or, plus, minus, divided, remainder, is, contains, joined,
rounded, split, read

**Special:** problem

These words are deliberately **not** reserved, so they can be used inside
names, even though they are special in certain positions: add, count, number,
list, first, last, time, seconds, file, random, current, version, result,
length, larger, smaller, square, root, absolute, value, uppercase, lowercase,
equal, greater, less, than, at, least, most, one, next, something, goes, wrong,
user, point.

For example `Set current time to 1.` is legal (the phrase `the current time`
only means the clock right after the word `the`), and a loop variable may be
called `count`.

## 5. Statements

### Variables

```
Set score to 10.
Set name to text Ada end text.
Set done to no.
Change score by 5.
Change score by negative 2.
Set item 2 of scores to 99.
```

`Set` creates the variable in the current place (global at the top level, local
inside a function). `Change` updates the nearest existing variable of that name
and is an error if none exists.

### Output and input

```
Say text Total is end text, total.      prints the values separated by spaces, then a new line
Write text no newline here. end text.   prints without a new line
Ask the user for name.                  stores the typed line as text
Ask the user for a number called age.   converts to a number, re-asks on bad input
```

### Conditions

```
If score is greater than 5, then
  Say text big end text
otherwise if score is equal to 5, then
  Say text five end text
otherwise
  Say text small end text
end if.
```

Any number of `otherwise if` branches and at most one `otherwise` branch. A
condition must produce `yes` or `no`; anything else is a runtime error.

### Loops

```
Repeat 10 times, ... end loop.
While count is less than 10, ... end loop.
For each item in shopping list, ... end loop.
Count from 1 to 10 using i, ... end loop.
Count from 0 to 100 using i by 5, ... end loop.
```

Inside any loop: `Stop the loop.` leaves it, `Skip to the next one.` jumps to
the next round. `Count` includes both ends and counts upward.

### Lists

```
Make a list called scores holding 5, 10, 15.
Add 20 to scores.
Remove the last item from scores.
Remove item 2 from scores.
Say item 1 of scores.                  item 1 is the first item
Set item 2 of scores to 99.
Say the length of scores.
If scores contains 10, then ... end if.
Sort scores.
Reverse scores.
Say the first item of scores.
Say the last item of scores.
```

### Functions

```
To add numbers with first and second, do
  give back first plus second.
end function.

Set answer to the result of add numbers with 3 and 4.
Run greet with text Bob end text.
```

Parameters are separated by `and`. `give back` returns a value; a function
without `give back` gives `nothing`. Functions see their own local variables
plus the global ones (closures over globals), support recursion, and each call
gets fresh locals.

### Errors

```
Try,
  Say item 99 of scores.
if something goes wrong,
  Say text Something broke: end text, the problem.
end try.
```

Only runtime problems are caught. Inside the handler, `the problem` holds the
error message.

### Files and imports

```
Say read file text notes.txt end text.
Write file text notes.txt end text with text hello end text.
Use the file text helpers.pln end text.
```

File names are relative to the folder of the running program. `Use the file`
runs another `.pln` file once, as part of this program; imported files are
remembered so a program cannot import the same file twice.

### Other built-ins

```
Say random number from 1 to 10.
Say the current time.
Wait 2 seconds.
Say the text version of 42.
Say the number version of text 3 point 5 end text.
```

## 6. Expressions and precedence

From loosest to tightest. Use `group ... end group` to force a different order.

| Level | Words | Notes |
| --- | --- | --- |
| 1 | `or` | left-associative |
| 2 | `and` | left-associative |
| 3 | `not` | prefix |
| 4 | comparisons: `is equal to`, `is not equal to`, `is greater than`, `is less than`, `is at least`, `is at most`; also `contains` | one comparison per level; chaining two is an error |
| 5 | `joined with` | text joining, left-associative |
| 6 | `plus`, `minus` | numbers only; use `joined with` for text |
| 7 | `times`, `divided by`, `remainder of` | left-associative |
| 8 | `to the power of` | right-associative |
| 9 | `negative`, `the square root of`, `the absolute value of`, `uppercase of`, `lowercase of` | prefix |
| 10 | `rounded` | postfix |
| 11 | literals, names, `group`, `item N of`, `the ...` phrases, calls, built-ins | primary |

## 7. Formal grammar (EBNF)

This is the grammar the parser follows, written in EBNF where `(*)` means zero
or more and `(*)?` means optional. Uppercase names are lexer tokens; lowercase
names are grammar rules; quoted words must appear literally (case-insensitive).

```ebnf
program        = { statement } ;

(* ---------- statements ---------- *)

statement      = set_stmt | change_stmt | if_stmt | while_stmt | repeat_stmt
               | foreach_stmt | count_stmt | say_stmt | write_stmt | ask_stmt
               | make_stmt | add_stmt | remove_stmt | sort_stmt | reverse_stmt
               | function_stmt | run_stmt | try_stmt | use_stmt | wait_stmt
               | giveback_stmt | stop_stmt | skip_stmt ;

set_stmt       = "set" name "to" expression end_statement
               | "set" "item" additive "of" name "to" expression end_statement ;

change_stmt    = "change" name "by" expression end_statement ;

if_stmt        = "if" expression [","] "then" block
                 { "otherwise" "if" expression [","] "then" block }
                 [ "otherwise" block ]
                 "end" "if" end_statement ;

while_stmt     = "while" expression [","] block "end" "loop" end_statement ;

repeat_stmt    = "repeat" power "times" [","] block "end" "loop" end_statement ;

foreach_stmt   = "for" "each" loop_name "in" expression [","] block
                 "end" "loop" end_statement ;

count_stmt     = "count" "from" expression "to" expression "using" name
                 [ "by" expression ] [","] block "end" "loop" end_statement ;

say_stmt       = "say" expression { "," expression } end_statement ;

write_stmt     = "write" expression { "," expression } end_statement
               | write_file_expr end_statement ;   (* run for effect *)

ask_stmt       = "ask" "the" "user" "for"
                 ( "a" "number" "called" name | name ) end_statement ;

make_stmt      = "make" "a" "list" "called" name
                 [ "holding" expression { "," expression } ] end_statement ;

add_stmt       = "add" expression "to" name end_statement ;

remove_stmt    = "remove" ( "the" "last" "item" "from" name
               | "item" expression "from" name ) end_statement ;

sort_stmt      = "sort" name end_statement ;
reverse_stmt   = "reverse" name end_statement ;

function_stmt  = "to" name [ "with" param { "and" param } ] [","]
                 "do" block "end" "function" end_statement ;
param          = name ;

run_stmt       = "run" name [ "with" call_arg { "and" call_arg } ]
                 end_statement ;

try_stmt       = "try" [","] block
                 [ "if" "something" "goes" "wrong" [","] block ]
                 "end" "try" end_statement ;

use_stmt       = "use" "the" "file" TEXT end_statement ;
wait_stmt      = "wait" expression "seconds" end_statement ;
giveback_stmt  = "give" "back" expression end_statement ;
stop_stmt      = "stop" "the" "loop" end_statement ;
skip_stmt      = "skip" "to" "the" "next" "one" end_statement ;

block          = { statement | "," } ;        (* stops at the matching end word *)
loop_name      = "item" | name ;              (* "item" allowed only here *)
end_statement  = "." ;                        (* see rule A below *)

(* ---------- expressions, loosest to tightest ---------- *)

expression     = or_expr ;
or_expr        = and_expr { "or" and_expr } ;
and_expr       = not_expr { "and" not_expr } ;
not_expr       = "not" not_expr | comparison ;
comparison     = concat [ comparison_tail ] ; (* see rule B below *)
comparison_tail= "is" compare_op concat | "contains" concat ;
compare_op     = "equal" "to" | "not" "equal" "to" | "greater" "than"
               | "less" "than" | "at" "least" | "at" "most" ;
concat         = additive { "joined" "with" additive } ;
additive       = multiplicative { ( "plus" | "minus" ) multiplicative } ;
multiplicative = power { ( "times" | "divided" "by" | "remainder" "of" ) power } ;
power          = unary [ "to" "the" "power" "of" power ] ;   (* right-assoc *)
unary          = "negative" unary
               | "the" "square" "root" "of" unary
               | "the" "absolute" "value" "of" unary
               | "uppercase" "of" unary
               | "lowercase" "of" unary
               | postfix ;
postfix        = primary [ "rounded" ] ;

primary        = NUMBER [ "point" NUMBER ]      (* decimal *)
               | TEXT
               | "yes" | "no" | "nothing"
               | "group" expression "end" "group"
               | item_of
               | the_phrase
               | "a" "list" "holding" expression { "," expression }
               | "random" "number" "from" additive "to" additive
               | "split" additive "by" additive
               | "read" "file" postfix
               | write_file_expr
               | name ;

item_of        = "item" additive "of" postfix   (* see rule C below *)
               | name ;                          (* a variable called item *)

write_file_expr= "write" "file" postfix "with" additive ;

the_phrase     = "the" "length" "of" postfix
               | "the" "larger" "of" comparison "and" comparison
               | "the" "smaller" "of" comparison "and" comparison
               | "the" "first" "item" "of" postfix
               | "the" "last" "item" "of" postfix
               | "the" "result" "of" name [ "with" call_arg { "and" call_arg } ]
               | "the" "number" "version" "of" postfix
               | "the" "text" "version" "of" postfix
               | "the" "current" "time"
               | "the" "problem" ;

call_arg       = comparison ;                   (* see rule D below *)

name           = WORD { WORD } ;                (* no reserved words inside *)

(* ---------- lexer tokens ---------- *)

NUMBER         = digit { digit } ;
TEXT           = "text" , any characters , "end text" ;
WORD           = letter { letter } ;            (* at least one letter; digits
                                                    may not touch a word *)
COMMA          = "," ;
PERIOD         = "." ;
```

## 8. Ambiguity decisions

Where two phrasings could conflict, one was chosen and written down here. The
parser follows these rules exactly.

**A. A period may end a text literal.** The spec's own example contains
`text You got it in end text, tries, text tries. end text` — a statement whose
text ends with a period. Rule: after a statement whose last token is a text
literal ending in `.`, the trailing statement period is optional. Everywhere
else the period is required.

**B. Comparisons do not chain.** `1 is less than x is less than 10` is an error
with the suggestion to use `group ... end group` for each step. One comparison
per expression keeps the meaning unambiguous.

**C. The word `item`.** `item` is reserved (so names cannot contain it), but it
is allowed as the loop variable in `For each item in ...`. In an expression,
`item N of X` is indexing; if what follows `item` is not a valid index, the
word is read as the loop variable `item` instead.

**D. Commas and `and` inside function calls.** Call arguments are separated by
`and`, and each argument is parsed at the comparison level, so `the result of f
with 2 and 3` passes two inputs. Inside an argument, `plus` or `minus` followed
by `the result of` ends the argument and belongs to the enclosing expression:
`the result of f with 1 plus the result of g with 2` calls `f` with 1 and `g`
with 2, rather than trying to add a call to a call.

**E. Commas bind to the innermost list.** In `a list holding 1, a list holding
2, 3, 4`, the commas join the nearest open list: the outer list gets one item,
which is the list `2, 3, 4`. Write `group ... end group` around an inner list
if you want it to be a single item among others.

**F. The `Repeat` count is not a multiplication.** In `Repeat 3 times, ...`
the count is parsed at the power level, so `times` is read as the loop keyword,
never as the multiplication operator.

**G. `Set` defines, `Change` updates.** `Set` creates the variable in the
current scope (a function's own local scope, or the global scope).
`Change X by N` finds the nearest existing `X` walking outward and is a runtime
error if none exists. This makes a function's local `Set total to 0.` unable to
clobber the global `total` by accident.

**H. Conditions must be yes or no.** Using a number or text as an `if` or
`while` condition is a runtime error, not a silent truthiness rule.

**I. `plus` is for numbers, `joined with` is for text.** Adding two pieces of
text with `plus` is an error whose fix suggests `joined with`. Joining a number
with text using `joined with` converts the number to text automatically.

**J. `Say` joins with spaces, `Write` does not.** `Say a, b, c` prints the
values separated by single spaces and then a new line. `Write a, b, c` prints
the values with nothing between them and no new line.

**K. Text literal boundaries.** The content of a text literal is everything
between the first space after `text` and the last space before `end text`. So
`text   end text` holds one space, `text end text` holds nothing, and periods
and commas may appear inside. A text literal cannot contain the words
`end text`, and a note cannot contain the words `end note`.

**L. `the text version of` is an operator, not a literal.** The lexer treats
the phrase `text version of` specially so `the text version of 42` is a
conversion, not a text literal that happens to start with `text`.

**M. Case does not matter, names are maximal.** Keywords and names are matched
case-insensitively, and a name is the longest run of non-reserved words, so
`Set total score to 1.` makes one variable called `total score`.

## 9. Error messages

Every error quotes the line it happened on, explains the problem in one
sentence, and suggests a fix:

```
I found a runtime problem on line 3 of the Plain program:
    Say item 5 of scores.
I cannot give item 5 of a list that has only 3 items on line 3.
Use a item number from 1 to 3, or check the length of the list first.
```

Syntax errors from the lexer name the forbidden symbol and the word to use
instead. Runtime errors from the interpreter explain what went wrong in plain
words. The `plain check` command reports these without running the program.
