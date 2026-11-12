"""The Plain interpreter.

A tree-walking evaluator.  Values are:
    numbers  -> Python int or float
    text     -> Python str
    truth    -> Python bool (yes / no)
    nothing  -> None
    lists    -> Python list (may hold any mix of values)
"""

import os
import sys

from plain.errors import PlainError, PlainRuntimeError
from plain.builtins import (
    is_number, display_value, describe_type, to_text, to_number,
    builtin_random, builtin_current_time, builtin_wait, builtin_split,
    builtin_read_file, builtin_write_file, builtin_sqrt, builtin_rounded,
)
from plain.ast_nodes import (
    Program, SetVar, SetItem, ChangeBy, If, While, Repeat, ForEach,
    CountLoop, Say, Write, Ask, MakeList, AddTo, RemoveLast, RemoveItem,
    SortList, ReverseList, FunctionDef, RunCall, TryBlock, UseFile,
    WaitStmt, GiveBack, StopLoop, SkipOne, Discard,
    Number, TextLiteral, Bool, Nothing, Var, ListLiteral, BinOp, Compare,
    Contains, Joined, And, Or, Not, Negative, SquareRoot, AbsoluteValue,
    Rounded, LargerOf, SmallerOf, ItemOf, LengthOf, FirstItemOf,
    LastItemOf, UppercaseOf, LowercaseOf, ToText, ToNumber, Call,
    RandomNumber, CurrentTime, SplitText, ReadFile, WriteFile, TheProblem,
)


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class StopLoopSignal(Exception):
    pass


class SkipOneSignal(Exception):
    pass


class Scope:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name, line, source=None):
        scope = self
        while scope is not None:
            if name in scope.vars:
                return scope.vars[name]
            scope = scope.parent
        raise PlainRuntimeError(
            "I could not find a variable called %s on line %s." % (name, line),
            "Set it first, for example: Set %s to 0." % name.split()[0],
            line=line, source=source)

    def set(self, name, value):
        scope = self
        while scope is not None:
            if name in scope.vars:
                scope.vars[name] = value
                return
            scope = scope.parent
        self.vars[name] = value

    def define(self, name, value):
        self.vars[name] = value


class Function:
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body


class Interpreter:
    def __init__(self, source="", filename=None, output=None, input_fn=None):
        self.output = output if output is not None else (lambda s: sys.stdout.write(s))
        self.input_fn = input_fn if input_fn is not None else input
        self.source = source
        self.globals = Scope()
        self.functions = {}
        self.loaded_files = set()
        self.filename = os.path.abspath(filename) if filename else None

    # --- entry points -------------------------------------------------------

    def run(self, program):
        self.exec_block(program.statements, self.globals)

    def fail(self, line, problem, fix):
        raise PlainRuntimeError(problem, fix, line=line, source=self.source)

    # --- statements -----------------------------------------------------------

    def exec_block(self, statements, scope):
        for stmt in statements:
            self.exec_stmt(stmt, scope)

    def exec_stmt(self, stmt, scope):
        method = self._stmt_handlers.get(type(stmt))
        if method is None:
            self.fail(stmt.line, "I do not know how to run this statement.",
                      "This is a bug in Plain itself, not in your program.")
        method(self, stmt, scope)

    def _run_set_var(self, stmt, scope):
        # Set creates the variable in the current scope: global at the top
        # level, local inside a function. Change updates the nearest match.
        scope.define(stmt.name, self.eval(stmt.value, scope))

    def _run_set_item(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        index = self.eval(stmt.index, scope)
        value = self.eval(stmt.value, scope)
        self._check_list(container, stmt.name, stmt.line)
        pos = self._whole_index(index, stmt.line)
        if pos < 1 or pos > len(container):
            self.fail(stmt.line,
                      "I cannot set item %s of %s, because the list has %s." % (
                          pos, stmt.name, self._count_text(len(container))),
                      "Item numbers go from 1 to the length of the list.")
        container[pos - 1] = value

    def _run_change(self, stmt, scope):
        current = scope.get(stmt.name, stmt.line, self.source)
        amount = self.eval(stmt.amount, scope)
        if not is_number(current) or not is_number(amount):
            self.fail(stmt.line,
                      "I tried to change %s by %s on line %s, but change by works on numbers." % (
                          stmt.name, display_value(amount), stmt.line),
                      "change by adds a number to a number, for example: Change score by 5.")
        scope.set(stmt.name, current + amount)

    def _run_if(self, stmt, scope):
        for condition, block in stmt.branches:
            if self.truthy(self.eval(condition, scope), condition.line):
                self.exec_block(block, scope)
                return
        if stmt.otherwise is not None:
            self.exec_block(stmt.otherwise, scope)

    def _run_while(self, stmt, scope):
        while self.truthy(self.eval(stmt.condition, scope), stmt.condition.line):
            try:
                self.exec_block(stmt.body, scope)
            except SkipOneSignal:
                continue
            except StopLoopSignal:
                break

    def _run_repeat(self, stmt, scope):
        count = self.eval(stmt.count, scope)
        times = self._whole_number(count, stmt.line, "repeat")
        for _ in range(times):
            try:
                self.exec_block(stmt.body, scope)
            except SkipOneSignal:
                continue
            except StopLoopSignal:
                break

    def _run_for_each(self, stmt, scope):
        iterable = self.eval(stmt.iterable, scope)
        if not isinstance(iterable, list):
            self.fail(stmt.line,
                      "I tried to loop over %s on line %s, but for each works on lists." % (
                          describe_type(iterable), stmt.line),
                      "Loop over a list, for example: For each thing in shopping list, ... end loop.")
        for value in list(iterable):
            scope.define(stmt.name, value)
            try:
                self.exec_block(stmt.body, scope)
            except SkipOneSignal:
                continue
            except StopLoopSignal:
                break

    def _run_count(self, stmt, scope):
        start = self.eval(stmt.start, scope)
        stop = self.eval(stmt.stop, scope)
        start_n = self._whole_number(start, stmt.line, "count from")
        stop_n = self._whole_number(stop, stmt.line, "count to")
        if stmt.step is not None:
            step = self._whole_number(self.eval(stmt.step, scope), stmt.line, "by")
        else:
            step = 1
        if step == 0:
            self.fail(stmt.line,
                      "I cannot count by 0 on line %s, because the counter would never move." % stmt.line,
                      "Use by 1, by 2, by negative 1, or leave the step out.")
        values = list(range(start_n, stop_n + 1, step)) if step > 0 else list(range(start_n, stop_n - 1, step))
        for value in values:
            scope.define(stmt.name, value)
            try:
                self.exec_block(stmt.body, scope)
            except SkipOneSignal:
                continue
            except StopLoopSignal:
                break

    def _run_say(self, stmt, scope):
        parts = [display_value(self.eval(arg, scope)) for arg in stmt.args]
        self.output(" ".join(parts) + "\n")

    def _run_write(self, stmt, scope):
        parts = [display_value(self.eval(arg, scope)) for arg in stmt.args]
        self.output("".join(parts))

    def _run_ask(self, stmt, scope):
        while True:
            raw = self._read_input(stmt.line)
            if stmt.kind == "text":
                scope.set(stmt.name, raw)
                return
            try:
                value = to_number(raw, stmt.line)
            except PlainRuntimeError:
                self.output("That is not a number. Please type something like 42.\n")
                continue
            scope.set(stmt.name, value)
            return

    def _run_make_list(self, stmt, scope):
        scope.set(stmt.name, [self.eval(item, scope) for item in stmt.items])

    def _run_add_to(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        value = self.eval(stmt.value, scope)
        self._check_list(container, stmt.name, stmt.line)
        container.append(value)

    def _run_remove_last(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        self._check_list(container, stmt.name, stmt.line)
        if not container:
            self.fail(stmt.line,
                      "I tried to remove the last item of %s, but the list is already empty." % stmt.name,
                      "Check the length of the list before removing items.")
        container.pop()

    def _run_remove_item(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        self._check_list(container, stmt.name, stmt.line)
        index = self.eval(stmt.index, scope)
        pos = self._whole_index(index, stmt.line)
        if pos < 1 or pos > len(container):
            self.fail(stmt.line,
                      "I cannot remove item %s of %s, because the list has %s." % (
                          pos, stmt.name, self._count_text(len(container))),
                      "Item numbers go from 1 to the length of the list.")
        container.pop(pos - 1)

    def _run_sort(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        self._check_list(container, stmt.name, stmt.line)
        if all(is_number(v) for v in container):
            container.sort()
        elif all(isinstance(v, str) for v in container):
            container.sort()
        else:
            self.fail(stmt.line,
                      "I can only sort a list of all numbers or all text on line %s." % stmt.line,
                      "This list mixes kinds of values. Sort lists that hold one kind at a time.")

    def _run_reverse(self, stmt, scope):
        container = scope.get(stmt.name, stmt.line, self.source)
        self._check_list(container, stmt.name, stmt.line)
        container.reverse()

    def _run_function(self, stmt, scope):
        self.functions[stmt.name] = Function(stmt.name, stmt.params, stmt.body)

    def _run_run_call(self, stmt, scope):
        self.call_function(stmt.name, [self.eval(a, scope) for a in stmt.args], stmt.line)

    def _run_try(self, stmt, scope):
        try:
            self.exec_block(stmt.body, scope)
        except PlainRuntimeError as exc:
            if stmt.handler is None:
                return
            scope.define("problem", exc.problem)
            self.exec_block(stmt.handler, scope)

    def _run_use_file(self, stmt, scope):
        filename = stmt.filename
        if os.path.isabs(filename):
            path = filename
        else:
            base = os.path.dirname(self.filename) if self.filename else os.getcwd()
            path = os.path.join(base, filename)
            if not os.path.exists(path):
                path = os.path.abspath(filename)
        resolved = os.path.abspath(path)
        if resolved in self.loaded_files:
            return
        if not os.path.exists(resolved):
            self.fail(stmt.line,
                      "I could not find a file called %s on line %s." % (filename, stmt.line),
                      "Check the file name and where the file is saved.")
        with open(resolved, "r", encoding="utf-8") as handle:
            source = handle.read()
        from plain.lexer import lex
        from plain.parser import Parser
        self.loaded_files.add(resolved)
        tokens = lex(source)
        program = Parser(tokens, source).parse_program()
        saved = self.filename
        saved_source = self.source
        self.filename = resolved
        self.source = source
        try:
            self.exec_block(program.statements, self.globals)
        finally:
            self.filename = saved
            self.source = saved_source

    def _run_wait(self, stmt, scope):
        builtin_wait(self.eval(stmt.seconds, scope), stmt.line)

    def _run_give_back(self, stmt, scope):
        raise ReturnSignal(self.eval(stmt.value, scope))

    def _run_discard(self, stmt, scope):
        self.eval(stmt.value, scope)

    def _run_stop(self, stmt, scope):
        raise StopLoopSignal()

    def _run_skip(self, stmt, scope):
        raise SkipOneSignal()

    _stmt_handlers = {}

    # --- functions --------------------------------------------------------------

    def call_function(self, name, args, line):
        fn = self.functions.get(name)
        if fn is None:
            self.fail(line,
                      "I could not find a function called %s on line %s." % (name, line),
                      "Define it first, for example: To %s with a and b, do ... end function." % name.split()[0])
        if len(args) != len(fn.params):
            expected = " and ".join(fn.params) if fn.params else "no inputs"
            self.fail(line,
                      "The function %s expects %s input%s but I got %s on line %s." % (
                          name, len(fn.params), "" if len(fn.params) == 1 else "s",
                          len(args), line),
                      "Call it with the right inputs, for example: the result of %s with %s." % (
                          name, expected))
        call_scope = Scope(self.globals)
        for param, value in zip(fn.params, args):
            call_scope.define(param, value)
        try:
            self.exec_block(fn.body, call_scope)
        except ReturnSignal as signal:
            return signal.value
        return None

    # --- expressions ------------------------------------------------------------

    def eval(self, node, scope):
        method = self._eval_handlers.get(type(node))
        if method is None:
            self.fail(node.line, "I do not know how to work out this value.",
                      "This is a bug in Plain itself, not in your program.")
        return method(self, node, scope)

    def _eval_number(self, node, scope):
        return node.value

    def _eval_text(self, node, scope):
        return node.value

    def _eval_bool(self, node, scope):
        return node.value

    def _eval_nothing(self, node, scope):
        return None

    def _eval_var(self, node, scope):
        return scope.get(node.name, node.line, self.source)

    def _eval_list(self, node, scope):
        return [self.eval(item, scope) for item in node.items]

    def _eval_binop(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        if node.op == "plus":
            if is_number(left) and is_number(right):
                return left + right
            self.fail(node.line,
                      "I tried to work out %s plus %s on line %s, but plus works on numbers." % (
                          display_value(left), display_value(right), node.line),
                      "To glue text together, use joined with, for example: text a end text joined with text b end text")
        if node.op == "minus":
            self._need_numbers(left, right, node, "minus")
            return left - right
        if node.op == "times":
            self._need_numbers(left, right, node, "times")
            return left * right
        if node.op == "divided":
            self._need_numbers(left, right, node, "divided by")
            if right == 0:
                self.fail(node.line,
                          "I tried to divide %s by zero on line %s." % (display_value(left), node.line),
                          "Check the number after the words divided by.")
            return left / right
        if node.op == "remainder":
            self._need_numbers(left, right, node, "remainder of")
            if right == 0:
                self.fail(node.line,
                          "I tried to take the remainder of %s and zero on line %s." % (display_value(left), node.line),
                          "The number after the words remainder of cannot be zero.")
            return left % right
        if node.op == "power":
            self._need_numbers(left, right, node, "to the power of")
            try:
                result = left ** right
            except (OverflowError, ZeroDivisionError):
                self.fail(node.line,
                          "I could not work out %s to the power of %s on line %s." % (
                              display_value(left), display_value(right), node.line),
                          "Very large powers and zero to a negative power are not supported.")
            if isinstance(result, complex):
                self.fail(node.line,
                          "I could not work out %s to the power of %s on line %s, because the answer is not a real number." % (
                              display_value(left), display_value(right), node.line),
                          "Negative numbers only have whole-number powers in Plain.")
            return result
        self.fail(node.line, "I do not know the operator %s." % node.op,
                  "This is a bug in Plain itself, not in your program.")

    def _eval_compare(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        if node.op == "equal":
            return plain_equal(left, right)
        if node.op == "not_equal":
            return not plain_equal(left, right)
        # ordering comparisons
        if is_number(left) and is_number(right):
            pass
        elif isinstance(left, str) and isinstance(right, str):
            pass
        else:
            self.fail(node.line,
                      "I cannot compare %s and %s on line %s." % (
                          describe_type(left), describe_type(right), node.line),
                      "greater than, less than, at least and at most work on two numbers, or on two pieces of text in alphabetical order.")
        if node.op == "greater":
            return left > right
        if node.op == "less":
            return left < right
        if node.op == "at_least":
            return left >= right
        if node.op == "at_most":
            return left <= right
        self.fail(node.line, "I do not know the comparison %s." % node.op,
                  "This is a bug in Plain itself, not in your program.")

    def _eval_contains(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        if isinstance(left, list):
            return any(plain_equal(item, right) for item in left)
        if isinstance(left, str) and isinstance(right, str):
            return right in left
        self.fail(node.line,
                  "I cannot check whether %s contains %s on line %s." % (
                      describe_type(left), describe_type(right), node.line),
                  "contains works on a list with any value, or on text with text.")

    def _eval_joined(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        return to_text(left, node.line) + to_text(right, node.line)

    def _eval_and(self, node, scope):
        left = self.truthy(self.eval(node.left, scope), node.line)
        if not left:
            return False
        return self.truthy(self.eval(node.right, scope), node.line)

    def _eval_or(self, node, scope):
        left = self.truthy(self.eval(node.left, scope), node.line)
        if left:
            return True
        return self.truthy(self.eval(node.right, scope), node.line)

    def _eval_not(self, node, scope):
        return not self.truthy(self.eval(node.value, scope), node.line)

    def _eval_negative(self, node, scope):
        value = self.eval(node.value, scope)
        if not is_number(value):
            self.fail(node.line,
                      "negative needs a number on line %s, but I got %s." % (node.line, describe_type(value)),
                      "Write it like: negative 5")
        return -value

    def _eval_sqrt(self, node, scope):
        return builtin_sqrt(self.eval(node.value, scope), node.line)

    def _eval_abs(self, node, scope):
        value = self.eval(node.value, scope)
        if not is_number(value):
            self.fail(node.line,
                      "the absolute value of needs a number on line %s, but I got %s." % (
                          node.line, describe_type(value)),
                      "Write it like: the absolute value of negative 5")
        return abs(value)

    def _eval_rounded(self, node, scope):
        return builtin_rounded(self.eval(node.value, scope), node.line)

    def _eval_larger(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        self._need_orderable(left, right, node, "the larger of")
        return left if left > right else right

    def _eval_smaller(self, node, scope):
        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        self._need_orderable(left, right, node, "the smaller of")
        return left if left < right else right

    def _eval_item(self, node, scope):
        container = self.eval(node.container, scope)
        index = self.eval(node.index, scope)
        if not isinstance(container, list):
            self.fail(node.line,
                      "I tried to get an item of %s on line %s, but items live in lists." % (
                          describe_type(container), node.line),
                      "item works on lists, for example: item 1 of scores")
        pos = self._whole_index(index, node.line)
        if pos < 1 or pos > len(container):
            self.fail(node.line,
                      "I tried to get item %s of a list that has %s on line %s." % (
                          pos, self._count_text(len(container)), node.line),
                      "Item numbers go from 1 to the length of the list.")
        return container[pos - 1]

    def _eval_length(self, node, scope):
        value = self.eval(node.value, scope)
        if isinstance(value, (str, list)):
            return len(value)
        self.fail(node.line,
                  "the length of needs text or a list on line %s, but I got %s." % (
                      node.line, describe_type(value)),
                  "For example: the length of scores, or the length of text hello end text")

    def _eval_first(self, node, scope):
        value = self.eval(node.value, scope)
        self._need_list(value, node, "the first item of")
        if not value:
            self.fail(node.line,
                      "I tried to get the first item of an empty list on line %s." % node.line,
                      "Check the length of the list first.")
        return value[0]

    def _eval_last(self, node, scope):
        value = self.eval(node.value, scope)
        self._need_list(value, node, "the last item of")
        if not value:
            self.fail(node.line,
                      "I tried to get the last item of an empty list on line %s." % node.line,
                      "Check the length of the list first.")
        return value[-1]

    def _eval_upper(self, node, scope):
        value = self.eval(node.value, scope)
        if not isinstance(value, str):
            self.fail(node.line,
                      "uppercase of needs text on line %s, but I got %s." % (node.line, describe_type(value)),
                      "For example: uppercase of name")
        return value.upper()

    def _eval_lower(self, node, scope):
        value = self.eval(node.value, scope)
        if not isinstance(value, str):
            self.fail(node.line,
                      "lowercase of needs text on line %s, but I got %s." % (node.line, describe_type(value)),
                      "For example: lowercase of name")
        return value.lower()

    def _eval_to_text(self, node, scope):
        return to_text(self.eval(node.value, scope), node.line)

    def _eval_to_number(self, node, scope):
        return to_number(self.eval(node.value, scope), node.line)

    def _eval_call(self, node, scope):
        return self.call_function(node.name, [self.eval(a, scope) for a in node.args], node.line)

    def _eval_random(self, node, scope):
        return builtin_random(self.eval(node.start, scope), self.eval(node.stop, scope), node.line)

    def _eval_time(self, node, scope):
        return builtin_current_time()

    def _eval_split(self, node, scope):
        return builtin_split(self.eval(node.value, scope), self.eval(node.separator, scope), node.line)

    def _resolve_path(self, path):
        if os.path.isabs(path):
            return path
        base = os.path.dirname(self.filename) if self.filename else os.getcwd()
        return os.path.join(base, path)

    def _eval_read_file(self, node, scope):
        return builtin_read_file(self._resolve_path(self.eval(node.path, scope)), node.line)

    def _eval_write_file(self, node, scope):
        return builtin_write_file(self._resolve_path(self.eval(node.path, scope)), self.eval(node.content, scope), node.line)

    def _eval_problem(self, node, scope):
        scope_walk = scope
        while scope_walk is not None:
            if "problem" in scope_walk.vars:
                return scope_walk.vars["problem"]
            scope_walk = scope_walk.parent
        self.fail(node.line,
                  "the problem on line %s is only available inside the catch part of a try." % node.line,
                  "Use the problem between if something goes wrong and end try.")

    _eval_handlers = {}

    # --- shared helpers -----------------------------------------------------------

    def truthy(self, value, line):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        self.fail(line,
                  "A condition has to be yes or no on line %s, but I got %s." % (
                      line, describe_type(value)),
                  "Compare values with words like is equal to or is greater than, then use the answer as the condition.")

    def _need_numbers(self, left, right, node, words):
        if not (is_number(left) and is_number(right)):
            self.fail(node.line,
                      "I tried to use %s on %s and %s on line %s, but %s works on numbers." % (
                          words, describe_type(left), describe_type(right), node.line, words),
                      "Numbers can use plus, minus, times, divided by, remainder of and to the power of.")

    def _need_orderable(self, left, right, node, words):
        if (is_number(left) and is_number(right)) or (isinstance(left, str) and isinstance(right, str)):
            return
        self.fail(node.line,
                  "%s needs two numbers or two pieces of text on line %s, but I got %s and %s." % (
                      words, node.line, describe_type(left), describe_type(right)),
                  "Compare values of the same kind.")

    def _need_list(self, value, node, words):
        if not isinstance(value, list):
            self.fail(node.line,
                      "%s needs a list on line %s, but I got %s." % (words, node.line, describe_type(value)),
                      "For example: the first item of scores")

    def _check_list(self, value, name, line):
        if not isinstance(value, list):
            self.fail(line,
                      "%s is not a list on line %s, so this list instruction cannot work." % (name, line),
                      "Make a list first, for example: Make a list called %s." % name.split()[0])

    def _whole_number(self, value, line, words):
        if is_number(value) and float(value).is_integer():
            return int(value)
        self.fail(line,
                  "%s needs a whole number on line %s, but I got %s." % (words, line, display_value(value)),
                  "Use a whole number of times, steps or items.")

    def _whole_index(self, value, line):
        if is_number(value) and float(value).is_integer():
            return int(value)
        self.fail(line,
                  "Item numbers have to be whole numbers on line %s, but I got %s." % (
                      line, display_value(value)),
                  "Use a whole number, like item 2 of scores.")

    def _count_text(self, count):
        if count == 0:
            return "no items"
        if count == 1:
            return "1 item"
        return "%s items" % count

    def _read_input(self, line):
        try:
            return self.input_fn()
        except EOFError:
            self.fail(line,
                      "I could not read an answer on line %s, because there is no more input." % line,
                      "Give the program input, or run it in a terminal where you can type.")


Interpreter._stmt_handlers = {
    SetVar: Interpreter._run_set_var,
    Discard: Interpreter._run_discard,
    SetItem: Interpreter._run_set_item,
    ChangeBy: Interpreter._run_change,
    If: Interpreter._run_if,
    While: Interpreter._run_while,
    Repeat: Interpreter._run_repeat,
    ForEach: Interpreter._run_for_each,
    CountLoop: Interpreter._run_count,
    Say: Interpreter._run_say,
    Write: Interpreter._run_write,
    Ask: Interpreter._run_ask,
    MakeList: Interpreter._run_make_list,
    AddTo: Interpreter._run_add_to,
    RemoveLast: Interpreter._run_remove_last,
    RemoveItem: Interpreter._run_remove_item,
    SortList: Interpreter._run_sort,
    ReverseList: Interpreter._run_reverse,
    FunctionDef: Interpreter._run_function,
    RunCall: Interpreter._run_run_call,
    TryBlock: Interpreter._run_try,
    UseFile: Interpreter._run_use_file,
    WaitStmt: Interpreter._run_wait,
    GiveBack: Interpreter._run_give_back,
    StopLoop: Interpreter._run_stop,
    SkipOne: Interpreter._run_skip,
}

Interpreter._eval_handlers = {
    Number: Interpreter._eval_number,
    TextLiteral: Interpreter._eval_text,
    Bool: Interpreter._eval_bool,
    Nothing: Interpreter._eval_nothing,
    Var: Interpreter._eval_var,
    ListLiteral: Interpreter._eval_list,
    BinOp: Interpreter._eval_binop,
    Compare: Interpreter._eval_compare,
    Contains: Interpreter._eval_contains,
    Joined: Interpreter._eval_joined,
    And: Interpreter._eval_and,
    Or: Interpreter._eval_or,
    Not: Interpreter._eval_not,
    Negative: Interpreter._eval_negative,
    SquareRoot: Interpreter._eval_sqrt,
    AbsoluteValue: Interpreter._eval_abs,
    Rounded: Interpreter._eval_rounded,
    LargerOf: Interpreter._eval_larger,
    SmallerOf: Interpreter._eval_smaller,
    ItemOf: Interpreter._eval_item,
    LengthOf: Interpreter._eval_length,
    FirstItemOf: Interpreter._eval_first,
    LastItemOf: Interpreter._eval_last,
    UppercaseOf: Interpreter._eval_upper,
    LowercaseOf: Interpreter._eval_lower,
    ToText: Interpreter._eval_to_text,
    ToNumber: Interpreter._eval_to_number,
    Call: Interpreter._eval_call,
    RandomNumber: Interpreter._eval_random,
    CurrentTime: Interpreter._eval_time,
    SplitText: Interpreter._eval_split,
    ReadFile: Interpreter._eval_read_file,
    WriteFile: Interpreter._eval_write_file,
    TheProblem: Interpreter._eval_problem,
}


def plain_equal(left, right):
    """Deep equality for Plain values."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if is_number(left) and is_number(right):
        return left == right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    if left is None and right is None:
        return True
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(plain_equal(a, b) for a, b in zip(left, right))
    return False
