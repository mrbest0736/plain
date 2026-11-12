"""The Plain fast runner.

Compiles the parsed AST into Python closures once, then executes the closures.
This removes the per-node dispatch and attribute lookups of the tree-walking
interpreter in interpreter.py, which stays the readable reference for exactly
what each construct does.  Both engines share the same Scope, the same signals
and the same error messages; tests/test_vm.py checks that they agree.
"""

import os
import sys

from plain.errors import PlainRuntimeError
from plain.builtins import (
    is_number, display_value, describe_type, to_text, to_number,
    builtin_random, builtin_current_time, builtin_wait, builtin_split,
    builtin_read_file, builtin_write_file, builtin_sqrt, builtin_rounded,
    builtin_secure_random,
)
from plain.security import (
    Limits, decrypt_text, encrypt_text, format_limit, secure_hash_text,
)
from plain.interpreter import (
    Scope, ReturnSignal, StopLoopSignal, SkipOneSignal, plain_equal,
)
from plain import ast_nodes as ast


class CompiledFunction:
    __slots__ = ("name", "params", "nparams", "body")

    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.nparams = len(params)
        self.body = body


class Runtime:
    """Holds the state of one running Plain program."""

    def __init__(self, source="", filename=None, output=None, input_fn=None, limits=None):
        self.output = output if output is not None else (lambda s: sys.stdout.write(s))
        self.input_fn = input_fn if input_fn is not None else input
        self.source = source
        self.globals = Scope()
        self.functions = {}
        self.loaded_files = set()
        self.filename = os.path.abspath(filename) if filename else None
        self.limits = limits if limits is not None else Limits()
        self.loop_rounds = 0
        self.depth = 0

    def fail(self, line, problem, fix):
        raise PlainRuntimeError(problem, fix, line=line, source=self.source)

    def run(self, program):
        self._guard_output()
        body = compile_block(program.statements, self)
        body(self, self.globals)

    def _guard_output(self):
        cap = self.limits.max_output_chars
        if cap is None:
            return
        raw = self.output
        if not callable(raw):
            raw = raw.append
        written = [0]

        def guarded(text):
            written[0] += len(text)
            if written[0] > cap:
                raise PlainRuntimeError(
                    "I stopped the program because it has said more than %s characters." % format_limit(cap),
                    "Look for a loop that prints more than it should, or raise the limit with --max-output-chars.")
            raw(text)
        self.output = guarded

    def _check_rounds(self, line):
        self.loop_rounds += 1
        cap = self.limits.max_loop_rounds
        if cap is not None and self.loop_rounds > cap:
            self.fail(line,
                      "I stopped this loop on line %s because the program has run more than %s loop rounds in total." % (
                          line, format_limit(cap)),
                      "This usually means the loop would never end. Make sure something inside the loop changes the condition, or raise the limit with --max-loop-rounds.")

    def call_function(self, name, args, line):
        fn = self.functions.get(name)
        if fn is None:
            self.fail(line,
                      "I could not find a function called %s on line %s." % (name, line),
                      "Define it first, for example: To %s with a and b, do ... end function." % name.split()[0])
        if len(args) != fn.nparams:
            expected = " and ".join(fn.params) if fn.params else "no inputs"
            self.fail(line,
                      "The function %s expects %s input%s but I got %s on line %s." % (
                          name, fn.nparams, "" if fn.nparams == 1 else "s",
                          len(args), line),
                      "Call it with the right inputs, for example: the result of %s with %s." % (
                          name, expected))
        call_scope = Scope(self.globals)
        call_scope.vars.update(zip(fn.params, args))
        self.depth += 1
        cap = self.limits.max_call_depth
        if cap is not None and self.depth > cap:
            self.depth -= 1
            self.fail(line,
                      "I stopped this call on line %s because functions are nested more than %s deep." % (
                          line, format_limit(cap)),
                      "This usually means a function keeps calling itself forever. Make sure the recursion has a stopping condition, or raise the limit with --max-call-depth.")
        try:
            result = fn.body(self, call_scope)
        finally:
            self.depth -= 1
        if result is not None:
            return result[0]
        return None

    def make_caller(self, name, arg_fns, line):
        """Build one closure reused by both the Call expression and RunCall."""
        functions_get = self.functions.get
        globals_scope = self.globals
        call_self = self
        max_depth = self.limits.max_call_depth

        def invoke(scope):
            fn = functions_get(name)
            if fn is None:
                call_self.fail(line,
                               "I could not find a function called %s on line %s." % (name, line),
                               "Define it first, for example: To %s with a and b, do ... end function." % name.split()[0])
            args = [fn_arg(scope) for fn_arg in arg_fns]
            if len(args) != fn.nparams:
                expected = " and ".join(fn.params) if fn.params else "no inputs"
                call_self.fail(line,
                               "The function %s expects %s input%s but I got %s on line %s." % (
                                   name, fn.nparams, "" if fn.nparams == 1 else "s",
                                   len(args), line),
                               "Call it with the right inputs, for example: the result of %s with %s." % (
                                   name, expected))
            call_self.depth += 1
            if max_depth is not None and call_self.depth > max_depth:
                call_self.depth -= 1
                call_self.fail(line,
                               "I stopped this call on line %s because functions are nested more than %s deep." % (
                                   line, format_limit(max_depth)),
                               "This usually means a function keeps calling itself forever. Make sure the recursion has a stopping condition, or raise the limit with --max-call-depth.")
            call_scope = Scope(globals_scope)
            call_scope.vars.update(zip(fn.params, args))
            try:
                result = fn.body(call_self, call_scope)
            finally:
                call_self.depth -= 1
            if result is not None:
                return result[0]
            return None
        return invoke

    def resolve_path(self, path, line):
        if not isinstance(path, str):
            self.fail(line,
                      "read file and write file need the file name as text on line %s, but I got %s." % (
                          line, describe_type(path)),
                      "Write it like: read file text notes.txt end text")
        base = os.path.dirname(self.filename) if self.filename else os.getcwd()
        base_real = os.path.realpath(base)
        full = path if os.path.isabs(path) else os.path.join(base, path)
        real = os.path.realpath(full)
        if real != base_real and not real.startswith(base_real + os.sep):
            self.fail(line,
                      "I can only open files that live in the same folder as the program on line %s, but %s points outside it." % (
                          line, path),
                      "Move the file next to the program and use its name, like read file text notes.txt end text.")
        return full

    def read_input(self, line):
        try:
            return self.input_fn()
        except EOFError:
            self.fail(line,
                      "I could not read an answer on line %s, because there is no more input." % line,
                      "Give the program input, or run it in a terminal where you can type.")


# --- shared helpers -----------------------------------------------------------

def _truthy(rt, value, line):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    rt.fail(line,
            "A condition has to be yes or no on line %s, but I got %s." % (
                line, describe_type(value)),
            "Compare values with words like is equal to or is greater than, then use the answer as the condition.")


def _whole_number(rt, value, line, words):
    if is_number(value) and float(value).is_integer():
        return int(value)
    rt.fail(line,
            "%s needs a whole number on line %s, but I got %s." % (words, line, display_value(value)),
            "Use a whole number of times, steps or items.")


def _whole_index(rt, value, line):
    if is_number(value) and float(value).is_integer():
        return int(value)
    rt.fail(line,
            "Item numbers have to be whole numbers on line %s, but I got %s." % (
                line, display_value(value)),
            "Use a whole number, like item 2 of scores.")


def _count_text(count):
    if count == 0:
        return "no items"
    if count == 1:
        return "1 item"
    return "%s items" % count


def _need_numbers(rt, left, right, line, words):
    rt.fail(line,
            "I tried to use %s on %s and %s on line %s, but %s works on numbers." % (
                words, describe_type(left), describe_type(right), line, words),
            "Numbers can use plus, minus, times, divided by, remainder of and to the power of.")


# --- expression compiler ------------------------------------------------------

def compile_expr(node, rt):
    kind = type(node)

    if kind is ast.Number or kind is ast.TextLiteral or kind is ast.Bool:
        value = node.value
        return lambda scope: value

    if kind is ast.Nothing:
        return lambda scope: None

    if kind is ast.CurrentTime:
        return lambda scope: builtin_current_time()

    if kind is ast.Var:
        name = node.name
        line = node.line
        source = rt.source

        def var(scope):
            s = scope
            while s is not None:
                v = s.vars
                if name in v:
                    return v[name]
                s = s.parent
            raise PlainRuntimeError(
                "I could not find a variable called %s on line %s." % (name, line),
                "Set it first, for example: Set %s to 0." % name.split()[0],
                line=line, source=source)
        return var

    if kind is ast.BinOp:
        return _compile_binop(node, rt)

    if kind is ast.Compare:
        return _compile_compare(node, rt)

    if kind is ast.ListLiteral:
        item_fns = [compile_expr(item, rt) for item in node.items]
        line = node.line

        def list_literal(scope):
            return [fn(scope) for fn in item_fns]
        return list_literal

    if kind is ast.Contains:
        left = compile_expr(node.left, rt)
        right = compile_expr(node.right, rt)
        line = node.line

        def contains(scope):
            a = left(scope)
            b = right(scope)
            if isinstance(a, list):
                return any(plain_equal(item, b) for item in a)
            if isinstance(a, str) and isinstance(b, str):
                return b in a
            rt.fail(line,
                    "I cannot check whether %s contains %s on line %s." % (
                        describe_type(a), describe_type(b), line),
                    "contains works on a list with any value, or on text with text.")
        return contains

    if kind is ast.Joined:
        left = compile_expr(node.left, rt)
        right = compile_expr(node.right, rt)
        line = node.line

        def joined(scope):
            return to_text(left(scope), line) + to_text(right(scope), line)
        return joined

    if kind is ast.And:
        left = compile_expr(node.left, rt)
        right = compile_expr(node.right, rt)
        line = node.line

        def and_op(scope):
            value = left(scope)
            if value is False or value is None:
                return False
            if value is not True:
                _truthy(rt, value, line)
            value = right(scope)
            if value is False or value is None:
                return False
            if value is not True:
                return _truthy(rt, value, line)
            return True
        return and_op

    if kind is ast.Or:
        left = compile_expr(node.left, rt)
        right = compile_expr(node.right, rt)
        line = node.line

        def or_op(scope):
            value = left(scope)
            if value is True:
                return True
            if value is not False and value is not None:
                _truthy(rt, value, line)
            value = right(scope)
            if value is True:
                return True
            if value is False or value is None:
                return False
            return _truthy(rt, value, line)
        return or_op

    if kind is ast.Not:
        inner = compile_expr(node.value, rt)
        line = node.line

        def not_op(scope):
            value = inner(scope)
            if value is True:
                return False
            if value is False or value is None:
                return True
            return not _truthy(rt, value, line)
        return not_op

    if kind is ast.Negative:
        inner = compile_expr(node.value, rt)
        line = node.line

        def negative(scope):
            value = inner(scope)
            if not is_number(value):
                rt.fail(line,
                        "negative needs a number on line %s, but I got %s." % (line, describe_type(value)),
                        "Write it like: negative 5")
            return -value
        return negative

    if kind is ast.SquareRoot:
        inner = compile_expr(node.value, rt)
        line = node.line
        return lambda scope: builtin_sqrt(inner(scope), line)

    if kind is ast.AbsoluteValue:
        inner = compile_expr(node.value, rt)
        line = node.line

        def absolute(scope):
            value = inner(scope)
            if not is_number(value):
                rt.fail(line,
                        "the absolute value of needs a number on line %s, but I got %s." % (
                            line, describe_type(value)),
                        "Write it like: the absolute value of negative 5")
            return abs(value)
        return absolute

    if kind is ast.Rounded:
        inner = compile_expr(node.value, rt)
        line = node.line
        return lambda scope: builtin_rounded(inner(scope), line)

    if kind is ast.LargerOf or kind is ast.SmallerOf:
        left = compile_expr(node.left, rt)
        right = compile_expr(node.right, rt)
        line = node.line
        words = "the larger of" if kind is ast.LargerOf else "the smaller of"

        def larger_smaller(scope):
            a = left(scope)
            b = right(scope)
            if not ((is_number(a) and is_number(b)) or (isinstance(a, str) and isinstance(b, str))):
                rt.fail(line,
                        "%s needs two numbers or two pieces of text on line %s, but I got %s and %s." % (
                            words, line, describe_type(a), describe_type(b)),
                        "Compare values of the same kind.")
            if kind is ast.LargerOf:
                return a if a > b else b
            return a if a < b else b
        return larger_smaller

    if kind is ast.ItemOf:
        index_fn = compile_expr(node.index, rt)
        container_fn = compile_expr(node.container, rt)
        line = node.line

        def item_of(scope):
            container = container_fn(scope)
            if not isinstance(container, list):
                rt.fail(line,
                        "I tried to get an item of %s on line %s, but items live in lists." % (
                            describe_type(container), line),
                        "item works on lists, for example: item 1 of scores")
            pos = _whole_index(rt, index_fn(scope), line)
            if pos < 1 or pos > len(container):
                rt.fail(line,
                        "I tried to get item %s of a list that has %s on line %s." % (
                            pos, _count_text(len(container)), line),
                        "Item numbers go from 1 to the length of the list.")
            return container[pos - 1]
        return item_of

    if kind is ast.LengthOf:
        inner = compile_expr(node.value, rt)
        line = node.line

        def length_of(scope):
            value = inner(scope)
            if isinstance(value, (str, list)):
                return len(value)
            rt.fail(line,
                    "the length of needs text or a list on line %s, but I got %s." % (
                        line, describe_type(value)),
                    "For example: the length of scores, or the length of text hello end text")
        return length_of

    if kind is ast.FirstItemOf or kind is ast.LastItemOf:
        inner = compile_expr(node.value, rt)
        line = node.line
        words = "the first item of" if kind is ast.FirstItemOf else "the last item of"
        pick = 0 if kind is ast.FirstItemOf else -1

        def first_last(scope):
            value = inner(scope)
            if not isinstance(value, list):
                rt.fail(line,
                        "%s needs a list on line %s, but I got %s." % (words, line, describe_type(value)),
                        "For example: the first item of scores")
            if not value:
                rt.fail(line,
                        "I tried to get the %s of an empty list on line %s." % (
                            "first item" if pick == 0 else "last item", line),
                        "Check the length of the list first.")
            return value[pick]
        return first_last

    if kind is ast.UppercaseOf or kind is ast.LowercaseOf:
        inner = compile_expr(node.value, rt)
        line = node.line
        words = "uppercase of" if kind is ast.UppercaseOf else "lowercase of"

        def change_case(scope):
            value = inner(scope)
            if not isinstance(value, str):
                rt.fail(line,
                        "%s needs text on line %s, but I got %s." % (words, line, describe_type(value)),
                        "For example: %s name" % words)
            return value.upper() if kind is ast.UppercaseOf else value.lower()
        return change_case

    if kind is ast.ToText:
        inner = compile_expr(node.value, rt)
        line = node.line
        return lambda scope: to_text(inner(scope), line)

    if kind is ast.ToNumber:
        inner = compile_expr(node.value, rt)
        line = node.line
        return lambda scope: to_number(inner(scope), line)

    if kind is ast.Call:
        return rt.make_caller(node.name, [compile_expr(a, rt) for a in node.args], node.line)

    if kind is ast.RandomNumber:
        start_fn = compile_expr(node.start, rt)
        stop_fn = compile_expr(node.stop, rt)
        line = node.line

        def random_number(scope):
            return builtin_random(start_fn(scope), stop_fn(scope), line)
        return random_number

    if kind is ast.SecureRandom:
        start_fn = compile_expr(node.start, rt)
        stop_fn = compile_expr(node.stop, rt)
        line = node.line

        def secure_random(scope):
            return builtin_secure_random(start_fn(scope), stop_fn(scope), line)
        return secure_random

    if kind is ast.SecureHash:
        value_fn = compile_expr(node.value, rt)
        line = node.line

        def secure_hash(scope):
            value = value_fn(scope)
            if not isinstance(value, str):
                rt.fail(line,
                        "the secure hash of works on text on line %s, but I got %s." % (
                            line, describe_type(value)),
                        "Use the text version of to turn a value into text first.")
            return secure_hash_text(value)
        return secure_hash

    if kind is ast.Encrypt:
        value_fn = compile_expr(node.value, rt)
        key_fn = compile_expr(node.key, rt)
        line = node.line

        def encrypt(scope):
            value = value_fn(scope)
            key = key_fn(scope)
            if not isinstance(value, str) or not isinstance(key, str):
                rt.fail(line,
                        "encrypt works on text and a key made of text on line %s, but I got %s and %s." % (
                            line, describe_type(value), describe_type(key)),
                        "Write it like: encrypt message with key text our secret end text.")
            return encrypt_text(value, key)
        return encrypt

    if kind is ast.Decrypt:
        value_fn = compile_expr(node.value, rt)
        key_fn = compile_expr(node.key, rt)
        line = node.line

        def decrypt(scope):
            value = value_fn(scope)
            key = key_fn(scope)
            if not isinstance(value, str) or not isinstance(key, str):
                rt.fail(line,
                        "decrypt works on text and a key made of text on line %s, but I got %s and %s." % (
                            line, describe_type(value), describe_type(key)),
                        "Write it like: decrypt locked with key text our secret end text.")
            try:
                return decrypt_text(value, key)
            except ValueError:
                rt.fail(line,
                        "I cannot decrypt this message on line %s. The key may be wrong, or the text is not a Plain-encrypted message." % line,
                        "Decrypt it with the same key it was encrypted with.")
        return decrypt

    if kind is ast.SplitText:
        value_fn = compile_expr(node.value, rt)
        sep_fn = compile_expr(node.separator, rt)
        line = node.line

        def split(scope):
            return builtin_split(value_fn(scope), sep_fn(scope), line)
        return split

    if kind is ast.ReadFile:
        path_fn = compile_expr(node.path, rt)
        line = node.line

        def read_file(scope):
            return builtin_read_file(rt.resolve_path(path_fn(scope), line), line,
                                     max_bytes=rt.limits.max_read_bytes)
        return read_file

    if kind is ast.WriteFile:
        path_fn = compile_expr(node.path, rt)
        content_fn = compile_expr(node.content, rt)
        line = node.line

        def write_file(scope):
            return builtin_write_file(rt.resolve_path(path_fn(scope), line), content_fn(scope), line)
        return write_file

    if kind is ast.TheProblem:
        line = node.line
        source = rt.source

        def the_problem(scope):
            s = scope
            while s is not None:
                if "problem" in s.vars:
                    return s.vars["problem"]
                s = s.parent
            raise PlainRuntimeError(
                "the problem on line %s is only available inside the catch part of a try." % line,
                "Use the problem between if something goes wrong and end try.",
                line=line, source=source)
        return the_problem

    rt.fail(node.line, "I do not know how to work out this value.",
            "This is a bug in Plain itself, not in your program.")


def _compile_binop(node, rt):
    op = node.op
    left = compile_expr(node.left, rt)
    right = compile_expr(node.right, rt)
    line = node.line

    if op == "plus":
        def plus(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                return a + b
            rt.fail(line,
                    "I tried to work out %s plus %s on line %s, but plus works on numbers." % (
                        display_value(a), display_value(b), line),
                    "To glue text together, use joined with, for example: text a end text joined with text b end text")
        return plus

    if op == "minus":
        def minus(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                return a - b
            _need_numbers(rt, a, b, line, "minus")
        return minus

    if op == "times":
        def times(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                return a * b
            _need_numbers(rt, a, b, line, "times")
        return times

    if op == "divided":
        def divided(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                if b == 0:
                    rt.fail(line,
                            "I tried to divide %s by zero on line %s." % (display_value(a), line),
                            "Check the number after the words divided by.")
                return a / b
            _need_numbers(rt, a, b, line, "divided by")
        return divided

    if op == "remainder":
        def remainder(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                if b == 0:
                    rt.fail(line,
                            "I tried to take the remainder of %s and zero on line %s." % (display_value(a), line),
                            "The number after the words remainder of cannot be zero.")
                return a % b
            _need_numbers(rt, a, b, line, "remainder of")
        return remainder

    def power(scope):
        a = left(scope)
        b = right(scope)
        ta = type(a)
        tb = type(b)
        if not ((ta is int or ta is float) and (tb is int or tb is float)):
            _need_numbers(rt, a, b, line, "to the power of")
        try:
            result = a ** b
        except (OverflowError, ZeroDivisionError):
            rt.fail(line,
                    "I could not work out %s to the power of %s on line %s." % (
                        display_value(a), display_value(b), line),
                    "Very large powers and zero to a negative power are not supported.")
        if isinstance(result, complex):
            rt.fail(line,
                    "I could not work out %s to the power of %s on line %s, because the answer is not a real number." % (
                        display_value(a), display_value(b), line),
                    "Negative numbers only have whole-number powers in Plain.")
        return result
    return power


def _compile_compare(node, rt):
    op = node.op
    left = compile_expr(node.left, rt)
    right = compile_expr(node.right, rt)
    line = node.line

    if op == "equal":
        return lambda scope: plain_equal(left(scope), right(scope))
    if op == "not_equal":
        return lambda scope: not plain_equal(left(scope), right(scope))

    def make_compare(python_op):
        def compare(scope):
            a = left(scope)
            b = right(scope)
            ta = type(a)
            tb = type(b)
            if (ta is int or ta is float) and (tb is int or tb is float):
                return python_op(a, b)
            if ta is str and tb is str:
                return python_op(a, b)
            _check_orderable(rt, a, b, line)
            return python_op(a, b)
        return compare

    if op == "greater":
        return make_compare(lambda a, b: a > b)
    if op == "less":
        return make_compare(lambda a, b: a < b)
    if op == "at_least":
        return make_compare(lambda a, b: a >= b)
    return make_compare(lambda a, b: a <= b)


def _check_orderable(rt, a, b, line):
    if (is_number(a) and is_number(b)) or (isinstance(a, str) and isinstance(b, str)):
        return
    rt.fail(line,
            "I cannot compare %s and %s on line %s." % (describe_type(a), describe_type(b), line),
            "greater than, less than, at least and at most work on two numbers, or on two pieces of text in alphabetical order.")


# --- statement compiler -------------------------------------------------------

def compile_block(statements, rt):
    fns = [compile_stmt(stmt, rt) for stmt in statements]

    def block(rt_arg, scope):
        for fn in fns:
            result = fn(rt_arg, scope)
            if result is not None:
                return result
    return block


def compile_stmt(node, rt):
    kind = type(node)

    if kind is ast.SetVar:
        value_fn = compile_expr(node.value, rt)
        name = node.name

        def set_var(rt_arg, scope):
            scope.vars[name] = value_fn(scope)
        return set_var

    if kind is ast.SetItem:
        index_fn = compile_expr(node.index, rt)
        value_fn = compile_expr(node.value, rt)
        name = node.name
        line = node.line
        source = rt.source

        def set_item(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            value = value_fn(scope)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            pos = _whole_index(rt, index_fn(scope), line)
            if pos < 1 or pos > len(container):
                rt.fail(line,
                        "I cannot set item %s of %s, because the list has %s." % (
                            pos, name, _count_text(len(container))),
                        "Item numbers go from 1 to the length of the list.")
            container[pos - 1] = value
        return set_item

    if kind is ast.ChangeBy:
        amount_fn = compile_expr(node.amount, rt)
        name = node.name
        line = node.line
        source = rt.source

        def change_by(rt_arg, scope):
            s = scope
            while s is not None:
                v = s.vars
                if name in v:
                    current = v[name]
                    break
                s = s.parent
            else:
                raise PlainRuntimeError(
                    "I could not find a variable called %s on line %s." % (name, line),
                    "Set it first, for example: Set %s to 0." % name.split()[0],
                    line=line, source=source)
            amount = amount_fn(scope)
            tc = type(current)
            ta = type(amount)
            if not ((tc is int or tc is float) and (ta is int or ta is float)):
                rt.fail(line,
                        "I tried to change %s by %s on line %s, but change by works on numbers." % (
                            name, display_value(amount), line),
                        "change by adds a number to a number, for example: Change score by 5.")
            _assign_nearest(scope, name, current + amount)
        return change_by

    if kind is ast.If:
        branches = [(compile_expr(condition, rt), compile_block(block, rt), condition.line)
                    for condition, block in node.branches]
        otherwise = compile_block(node.otherwise, rt) if node.otherwise is not None else None

        def if_stmt(rt_arg, scope):
            for condition_fn, body, cond_line in branches:
                value = condition_fn(scope)
                if value is False or value is None:
                    continue
                if value is not True:
                    _truthy(rt_arg, value, cond_line)
                result = body(rt_arg, scope)
                if result is not None:
                    return result
                return
            if otherwise is not None:
                result = otherwise(rt_arg, scope)
                if result is not None:
                    return result
        return if_stmt

    if kind is ast.While:
        condition_fn = compile_expr(node.condition, rt)
        body = compile_block(node.body, rt)
        cond_line = node.condition.line

        def while_stmt(rt_arg, scope):
            while True:
                value = condition_fn(scope)
                if value is False or value is None:
                    break
                if value is not True:
                    _truthy(rt_arg, value, cond_line)
                rt_arg._check_rounds(node.line)
                try:
                    result = body(rt_arg, scope)
                except SkipOneSignal:
                    continue
                except StopLoopSignal:
                    break
                if result is not None:
                    return result
        return while_stmt

    if kind is ast.Repeat:
        count_fn = compile_expr(node.count, rt)
        body = compile_block(node.body, rt)
        line = node.line

        def repeat(rt_arg, scope):
            times = _whole_number(rt_arg, count_fn(scope), line, "repeat")
            for _ in range(times):
                rt_arg._check_rounds(line)
                try:
                    result = body(rt_arg, scope)
                except SkipOneSignal:
                    continue
                except StopLoopSignal:
                    break
                if result is not None:
                    return result
        return repeat

    if kind is ast.ForEach:
        iterable_fn = compile_expr(node.iterable, rt)
        body = compile_block(node.body, rt)
        name = node.name
        line = node.line

        def for_each(rt_arg, scope):
            iterable = iterable_fn(scope)
            if not isinstance(iterable, list):
                rt.fail(line,
                        "I tried to loop over %s on line %s, but for each works on lists." % (
                            describe_type(iterable), line),
                        "Loop over a list, for example: For each thing in shopping list, ... end loop.")
            values = list(iterable)
            for value in values:
                rt_arg._check_rounds(line)
                scope.vars[name] = value
                try:
                    result = body(rt_arg, scope)
                except SkipOneSignal:
                    continue
                except StopLoopSignal:
                    break
                if result is not None:
                    return result
        return for_each

    if kind is ast.CountLoop:
        start_fn = compile_expr(node.start, rt)
        stop_fn = compile_expr(node.stop, rt)
        step_fn = compile_expr(node.step, rt) if node.step is not None else None
        body = compile_block(node.body, rt)
        name = node.name
        line = node.line

        def count_loop(rt_arg, scope):
            start = _whole_number(rt_arg, start_fn(scope), line, "count from")
            stop = _whole_number(rt_arg, stop_fn(scope), line, "count to")
            if step_fn is not None:
                step = _whole_number(rt_arg, step_fn(scope), line, "by")
            else:
                step = 1
            if step == 0:
                rt.fail(line,
                        "I cannot count by 0 on line %s, because the counter would never move." % line,
                        "Use by 1, by 2, by negative 1, or leave the step out.")
            if step > 0:
                values = range(start, stop + 1, step)
            else:
                values = range(start, stop - 1, step)
            for value in values:
                rt_arg._check_rounds(line)
                scope.vars[name] = value
                try:
                    result = body(rt_arg, scope)
                except SkipOneSignal:
                    continue
                except StopLoopSignal:
                    break
                if result is not None:
                    return result
        return count_loop

    if kind is ast.Say:
        arg_fns = [compile_expr(a, rt) for a in node.args]

        def say(rt_arg, scope):
            rt_arg.output(" ".join([display_value(fn(scope)) for fn in arg_fns]) + "\n")
        return say

    if kind is ast.Write:
        arg_fns = [compile_expr(a, rt) for a in node.args]

        def write(rt_arg, scope):
            rt_arg.output("".join([display_value(fn(scope)) for fn in arg_fns]))
        return write

    if kind is ast.Ask:
        name = node.name
        kind_ask = node.kind
        line = node.line

        def ask(rt_arg, scope):
            while True:
                raw = rt_arg.read_input(line)
                if kind_ask == "text":
                    _assign_nearest(scope, name, raw)
                    return
                try:
                    value = to_number(raw, line)
                except PlainRuntimeError:
                    rt_arg.output("That is not a number. Please type something like 42.\n")
                    continue
                _assign_nearest(scope, name, value)
                return
        return ask

    if kind is ast.MakeList:
        item_fns = [compile_expr(item, rt) for item in node.items]
        name = node.name

        def make_list(rt_arg, scope):
            scope.vars[name] = [fn(scope) for fn in item_fns]
        return make_list

    if kind is ast.AddTo:
        value_fn = compile_expr(node.value, rt)
        name = node.name
        line = node.line
        source = rt.source

        def add_to(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            container.append(value_fn(scope))
        return add_to

    if kind is ast.RemoveLast:
        name = node.name
        line = node.line
        source = rt.source

        def remove_last(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            if not container:
                rt.fail(line,
                        "I tried to remove the last item of %s, but the list is already empty." % name,
                        "Check the length of the list before removing items.")
            container.pop()
        return remove_last

    if kind is ast.RemoveItem:
        index_fn = compile_expr(node.index, rt)
        name = node.name
        line = node.line
        source = rt.source

        def remove_item(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            pos = _whole_index(rt, index_fn(scope), line)
            if pos < 1 or pos > len(container):
                rt.fail(line,
                        "I cannot remove item %s of %s, because the list has %s." % (
                            pos, name, _count_text(len(container))),
                        "Item numbers go from 1 to the length of the list.")
            container.pop(pos - 1)
        return remove_item

    if kind is ast.SortList:
        name = node.name
        line = node.line
        source = rt.source

        def sort_list(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            if all(is_number(v) for v in container):
                container.sort()
            elif all(isinstance(v, str) for v in container):
                container.sort()
            else:
                rt.fail(line,
                        "I can only sort a list of all numbers or all text on line %s." % line,
                        "This list mixes kinds of values. Sort lists that hold one kind at a time.")
        return sort_list

    if kind is ast.ReverseList:
        name = node.name
        line = node.line
        source = rt.source

        def reverse_list(rt_arg, scope):
            container = _find_var(scope, name, line, source)
            if not isinstance(container, list):
                rt.fail(line,
                        "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                        "Make a list first, for example: Make a list called %s." % name.split()[0])
            container.reverse()
        return reverse_list

    if kind is ast.FunctionDef:
        body = compile_block(node.body, rt)
        fn = CompiledFunction(node.name, node.params, body)

        def define_function(rt_arg, scope):
            rt_arg.functions[node.name] = fn
        return define_function

    if kind is ast.RunCall:
        invoke = rt.make_caller(node.name, [compile_expr(a, rt) for a in node.args], node.line)

        def run_call(rt_arg, scope):
            invoke(scope)
        return run_call

    if kind is ast.TryBlock:
        body = compile_block(node.body, rt)
        handler = compile_block(node.handler, rt) if node.handler is not None else None

        def try_block(rt_arg, scope):
            try:
                result = body(rt_arg, scope)
            except PlainRuntimeError as exc:
                if handler is None:
                    return
                scope.vars["problem"] = exc.problem
                result = handler(rt_arg, scope)
            if result is not None:
                return result
        return try_block

    if kind is ast.UseFile:
        filename = node.filename
        line = node.line

        def use_file(rt_arg, scope):
            resolved = os.path.realpath(rt_arg.resolve_path(filename, line))
            if resolved in rt_arg.loaded_files:
                return
            if not os.path.exists(resolved):
                rt_arg.fail(line,
                            "I could not find a file called %s on line %s." % (filename, line),
                            "Check the file name and where the file is saved.")
            with open(resolved, "r", encoding="utf-8") as handle:
                imported_source = handle.read()
            from plain.lexer import lex
            from plain.parser import Parser
            rt_arg.loaded_files.add(resolved)
            imported = Parser(lex(imported_source), imported_source).parse_program()
            saved = rt_arg.filename
            saved_source = rt_arg.source
            rt_arg.filename = resolved
            rt_arg.source = imported_source
            try:
                imported_body = compile_block(imported.statements, rt_arg)
                imported_body(rt_arg, rt_arg.globals)
            finally:
                rt_arg.filename = saved
                rt_arg.source = saved_source
        return use_file

    if kind is ast.WaitStmt:
        seconds_fn = compile_expr(node.seconds, rt)
        line = node.line

        def wait(rt_arg, scope):
            builtin_wait(seconds_fn(scope), line, max_seconds=rt_arg.limits.max_wait_seconds)
        return wait

    if kind is ast.GiveBack:
        value_fn = compile_expr(node.value, rt)

        def give_back(rt_arg, scope):
            return (value_fn(scope),)
        return give_back

    if kind is ast.Discard:
        value_fn = compile_expr(node.value, rt)

        def discard(rt_arg, scope):
            value_fn(scope)
        return discard

    if kind is ast.StopLoop:
        def stop_loop(rt_arg, scope):
            raise StopLoopSignal()
        return stop_loop

    if kind is ast.SkipOne:
        def skip_one(rt_arg, scope):
            raise SkipOneSignal()
        return skip_one

    rt.fail(node.line, "I do not know how to run this statement.",
            "This is a bug in Plain itself, not in your program.")


def _find_var(scope, name, line, source):
    s = scope
    while s is not None:
        v = s.vars
        if name in v:
            return v[name]
        s = s.parent
    raise PlainRuntimeError(
        "I could not find a variable called %s on line %s." % (name, line),
        "Set it first, for example: Set %s to 0." % name.split()[0],
        line=line, source=source)


def _assign_nearest(scope, name, value):
    s = scope
    while s is not None:
        if name in s.vars:
            s.vars[name] = value
            return
        s = s.parent
    scope.vars[name] = value