"""Benchmark the two Plain engines against each other and against Python 3.

Run from the project root:  python3 tools/bench.py

The comparison against Python is honest context, not a competition: Plain is
an English-language teaching language hosted on CPython, so the same Python
runtime that runs Plain also runs the "Python" column below.
"""

import time

from plain.lexer import lex
from plain.parser import Parser
from plain.interpreter import Interpreter
from plain.vm import Runtime

FIB = """
To fib with n, do
  If n is less than 2, then give back n. end if.
  give back group the result of fib with n minus 1 end group plus group the result of fib with n minus 2 end group.
end function.
Say the result of fib with 22.
"""

COUNT_LOOP = """
Set total to 0.
Count from 1 to 200000 using i,
  Change total by 2.
end loop.
Say total.
"""

MATH_OPS = """
Set x to 1 point 5.
Repeat 100000 times,
  Set x to group x plus 2 end group times group x minus 1 end group plus group x divided by 3 end group.
  Set x to 1 point 5.
end loop.
Say x.
"""

LIST_OPS = """
Make a list called xs holding 1, 2, 3.
Repeat 30000 times,
  Add 4 to xs.
  Remove the last item from xs.
  Set item 1 of xs to 9.
end loop.
Say the length of xs.
"""

TEXT_OPS = """
Set t to text abc end text.
Repeat 50000 times,
  Set u to uppercase of t joined with the text version of 1.
end loop.
Say u.
"""

PYTHON_FIB = """
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
print(fib(22))
"""


def run_plain(src, engine):
    program = Parser(lex(src), src).parse_program()
    out = []
    eng = engine(source=src, output=out.append)
    start = time.perf_counter()
    eng.run(program)
    return time.perf_counter() - start, "".join(out).strip().splitlines()[-1]


def run_python(src):
    start = time.perf_counter()
    namespace = {}
    exec(src, namespace)
    return time.perf_counter() - start


def main():
    print("%-22s %10s %10s %9s" % ("benchmark", "reference", "compiled", "speedup"))
    for label, src in (("fib(22) recursion", FIB),
                       ("count loop 200k", COUNT_LOOP),
                       ("math ops 100k", MATH_OPS),
                       ("list ops 30k", LIST_OPS),
                       ("text ops 50k", TEXT_OPS)):
        tree_time, answer = run_plain(src, Interpreter)
        vm_time, vm_answer = run_plain(src, Runtime)
        assert answer == vm_answer, (answer, vm_answer)
        print("%-22s %9.3fs %9.3fs %8.1fx" % (label, tree_time, vm_time, tree_time / vm_time))

    python_time = run_python(PYTHON_FIB)
    print()
    print("Same fib(22) written in Python 3 itself: %.4fs" % python_time)
    print("Plain is a teaching language that runs on CPython, so it cannot be")
    print("faster than the runtime that hosts it, let alone compiled languages")
    print("like C or Rust. The compiled runner exists to waste as little of that")
    print("host runtime as possible.")


if __name__ == "__main__":
    main()
