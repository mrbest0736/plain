"""The Plain parser.

A recursive-descent parser that follows the grammar in LANGUAGE_GUIDE.md
exactly.  It produces a Program node holding statement and expression
AST nodes.
"""

from plain.lexer import (
    WORD, NUMBER, TEXT, COMMA, PERIOD, EOF, RESERVED,
)
from plain.errors import PlainSyntaxError, PlainIncomplete, PlainError
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
    SecureRandom, SecureHash, Encrypt, Decrypt,
)

STATEMENT_STARTERS = (
    "set", "change", "if", "while", "repeat", "for", "count", "say",
    "write", "ask", "make", "add", "remove", "sort", "reverse", "to",
    "run", "try", "use", "wait", "give", "stop", "skip",
)


class Parser:
    def __init__(self, tokens, source=None):
        self.toks = tokens
        self.pos = 0
        self.source = source
        self.func_depth = 0
        self.loop_depth = 0
        self.prev = None

    # --- token helpers -----------------------------------------------------

    def peek(self, k=0):
        j = self.pos + k
        if j >= len(self.toks):
            j = len(self.toks) - 1
        return self.toks[j]

    def advance(self):
        tok = self.toks[self.pos]
        if tok.type != EOF:
            self.prev = tok
            self.pos += 1
        return tok

    def at_eof(self):
        return self.peek().type == EOF

    def check(self, k, word):
        t = self.peek(k)
        return t.type == WORD and t.value == word

    def at(self, *words):
        return all(self.check(i, w) for i, w in enumerate(words))

    def accept(self, *words):
        if self.at(*words):
            for _ in words:
                self.advance()
            return True
        return False

    def describe(self, tok):
        if tok.type == EOF:
            return "the end of the program"
        if tok.type == COMMA:
            return "a comma"
        if tok.type == PERIOD:
            return "a period"
        if tok.type == NUMBER:
            return "the number %s" % tok.value
        if tok.type == TEXT:
            return "a text literal"
        return "the word %s" % tok.text

    def syntax(self, problem, fix, line=None):
        if line is None:
            line = self.peek().line
        return PlainSyntaxError(problem, fix, line=line, source=self.source)

    def expect(self, *words):
        if not self.accept(*words):
            tok = self.peek()
            wanted = " ".join(words)
            if len(words) == 1:
                problem = "I expected the word %s on line %s, but I found %s." % (
                    wanted, tok.line, self.describe(tok))
            else:
                problem = "I expected the words %s on line %s, but I found %s." % (
                    wanted, tok.line, self.describe(tok))
            raise self.syntax(problem, "Check the spelling and order of the words on this line.")

    def expect_name(self, what="a name"):
        tok = self.peek()
        if tok.type == NUMBER:
            raise self.syntax(
                "I expected %s on line %s, but names never start with a number." % (what, tok.line),
                "Names use letters only, for example: total score.")
        words = []
        while self.peek().type == WORD and self.peek().value not in RESERVED:
            words.append(self.advance().value)
        if not words:
            raise self.syntax(
                "I expected %s on line %s, but I found %s." % (what, tok.line, self.describe(tok)),
                "A name is one or more plain words, for example: total score.")
        return " ".join(words)

    def incomplete(self, message):
        return PlainIncomplete(message)

    def end_statement(self):
        tok = self.peek()
        if tok.type == PERIOD:
            self.advance()
            return
        prev = self.prev
        if prev is not None and prev.type == TEXT and prev.value.rstrip().endswith("."):
            return
        problem = "I expected a period to end this statement on line %s, but I found %s." % (
            tok.line, self.describe(tok))
        if prev is not None and prev.type == TEXT:
            fix = "Every statement ends with a period. Write it after end text, or inside the text before end text."
        else:
            fix = "Every statement ends with a period. Add one at the end of the statement."
        raise self.syntax(problem, fix, line=tok.line)

    def skip_commas(self):
        while self.peek().type == COMMA:
            self.advance()

    # --- program and statements ---------------------------------------------

    def parse_program(self):
        statements = []
        while not self.at_eof():
            self.skip_commas()
            if self.at_eof():
                break
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        tok = self.peek()
        if tok.type == NUMBER:
            raise self.syntax(
                "A statement cannot start with the number %s on line %s." % (tok.value, tok.line),
                "Statements start with words like Set, Say, If or While. If you meant a decimal, write it with the word point, like 3 point 14.")
        if tok.type == PERIOD:
            raise self.syntax(
                "I found an extra period on line %s." % tok.line,
                "Remove the extra period; one period ends each statement.")
        if tok.type == TEXT:
            raise self.syntax(
                "A statement cannot start with a text literal on line %s." % tok.line,
                "Statements start with words like Set, Say, If or While, for example: Say text hello end text.")
        if tok.type != WORD:
            raise self.syntax(
                "I did not expect %s on line %s." % (self.describe(tok), tok.line),
                "Plain is written with words, commas and periods only.")
        word = tok.value
        if word == "set":
            if self.at("set", "item"):
                return self.parse_set_item()
            return self.parse_set_var()
        if word == "change":
            return self.parse_change()
        if word == "if":
            return self.parse_if()
        if word == "while":
            return self.parse_while()
        if word == "repeat":
            return self.parse_repeat()
        if word == "for":
            return self.parse_for_each()
        if word == "count":
            return self.parse_count()
        if word == "say":
            return self.parse_say()
        if word == "write":
            return self.parse_write()
        if word == "ask":
            return self.parse_ask()
        if word == "make":
            return self.parse_make_list()
        if word == "add":
            return self.parse_add_to()
        if word == "remove":
            return self.parse_remove()
        if word == "sort":
            return self.parse_sort()
        if word == "reverse":
            return self.parse_reverse()
        if word == "to":
            return self.parse_function()
        if word == "run":
            return self.parse_run()
        if word == "try":
            return self.parse_try()
        if word == "use":
            return self.parse_use()
        if word == "wait":
            return self.parse_wait()
        if word == "give":
            return self.parse_give_back()
        if word == "stop":
            return self.parse_stop()
        if word == "skip":
            return self.parse_skip()
        problem = "I do not know how to start a statement with the word %s on line %s." % (tok.text, tok.line)
        raise self.syntax(
            problem,
            "Statements start with words like Set, Change, If, While, Repeat, For each, Count, Say, Write, Ask, Make, Add, Remove, Sort, Reverse, To, Run, Try, Use, Wait, Give back, Stop or Skip.")

    def parse_block(self, *stops):
        statements = []
        while True:
            self.skip_commas()
            tok = self.peek()
            if tok.type == EOF:
                raise self.incomplete(
                    "The program ends in the middle of a block that starts on line %s. "
                    "Blocks finish with words like end if, end loop, end function or end try." % (self.block_start_line or tok.line))
            if any(self.at(*s) for s in stops):
                return statements
            statements.append(self.parse_statement())

    block_start_line = 0

    # --- individual statements ----------------------------------------------

    def parse_set_var(self):
        tok = self.peek()
        self.expect("set")
        name = self.expect_name("the name of the variable")
        self.expect("to")
        value = self.expression()
        node = SetVar(name, value)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_set_item(self):
        tok = self.peek()
        self.expect("set", "item")
        index = self.parse_additive()
        self.expect("of")
        name = self.expect_name("the name of the list")
        self.expect("to")
        value = self.expression()
        node = SetItem(name, index, value)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_change(self):
        tok = self.peek()
        self.expect("change")
        name = self.expect_name("the name of the variable")
        self.expect("by")
        amount = self.expression()
        node = ChangeBy(name, amount)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_if(self):
        tok = self.peek()
        self.expect("if")
        condition = self.expression()
        self.skip_commas()
        self.expect("then")
        self.block_start_line = tok.line
        branches = []
        block = self.parse_block(("otherwise",), ("end", "if"))
        branches.append((condition, block))
        otherwise = []
        while True:
            if self.at("otherwise", "if"):
                self.advance()
                self.advance()
                cond = self.expression()
                self.skip_commas()
                self.expect("then")
                block = self.parse_block(("otherwise",), ("end", "if"))
                branches.append((cond, block))
            elif self.at("otherwise"):
                self.advance()
                otherwise = self.parse_block(("end", "if"))
                break
            else:
                break
        self.expect("end", "if")
        node = If(branches, otherwise)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_while(self):
        tok = self.peek()
        self.expect("while")
        condition = self.expression()
        self.skip_commas()
        self.loop_depth += 1
        self.block_start_line = tok.line
        body = self.parse_block(("end", "loop"))
        self.loop_depth -= 1
        self.expect("end", "loop")
        node = While(condition, body)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_repeat(self):
        tok = self.peek()
        self.expect("repeat")
        # power level, so the word times is not read as multiplication
        count = self.parse_power()
        self.expect("times")
        self.skip_commas()
        self.loop_depth += 1
        self.block_start_line = tok.line
        body = self.parse_block(("end", "loop"))
        self.loop_depth -= 1
        self.expect("end", "loop")
        node = Repeat(count, body)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_for_each(self):
        tok = self.peek()
        self.expect("for")
        self.expect("each")
        name = self.parse_loop_name()
        self.expect("in")
        iterable = self.expression()
        self.skip_commas()
        self.loop_depth += 1
        self.block_start_line = tok.line
        body = self.parse_block(("end", "loop"))
        self.loop_depth -= 1
        self.expect("end", "loop")
        node = ForEach(name, iterable, body)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_loop_name(self):
        if self.peek().type == WORD and self.peek().value == "item":
            self.advance()
            return "item"
        return self.expect_name("the name of the loop variable")

    def parse_count(self):
        tok = self.peek()
        self.expect("count")
        self.expect("from")
        start = self.expression()
        self.expect("to")
        stop = self.expression()
        self.expect("using")
        name = self.expect_name("the name of the counter")
        step = None
        if self.accept("by"):
            step = self.expression()
        self.skip_commas()
        self.loop_depth += 1
        self.block_start_line = tok.line
        body = self.parse_block(("end", "loop"))
        self.loop_depth -= 1
        self.expect("end", "loop")
        node = CountLoop(start, stop, name, step, body)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_say(self):
        tok = self.peek()
        self.expect("say")
        args = [self.expression()]
        while self.peek().type == COMMA:
            self.advance()
            args.append(self.expression())
        node = Say(args)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_write(self):
        tok = self.peek()
        save = self.pos
        self.expect("write")
        if self.at("file"):
            # Write file ... with ... used as a statement: run it, show nothing
            self.pos = save
            value = self.expression()
            node = Discard(value)
            node.line = tok.line
            self.end_statement()
            return node
        args = [self.expression()]
        while self.peek().type == COMMA:
            self.advance()
            args.append(self.expression())
        node = Write(args)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_ask(self):
        tok = self.peek()
        self.expect("ask", "the", "user", "for")
        if self.at("a", "number", "called"):
            self.advance()
            self.advance()
            self.advance()
            name = self.expect_name("the name of the variable")
            kind = "number"
        else:
            name = self.expect_name("the name of the variable")
            kind = "text"
        node = Ask(name, kind)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_make_list(self):
        tok = self.peek()
        self.expect("make", "a", "list", "called")
        name = self.expect_name("the name of the list")
        items = []
        if self.accept("holding"):
            items.append(self.expression())
            while self.peek().type == COMMA:
                self.advance()
                items.append(self.expression())
        node = MakeList(name, items)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_add_to(self):
        tok = self.peek()
        self.expect("add")
        value = self.expression()
        self.expect("to")
        name = self.expect_name("the name of the list")
        node = AddTo(value, name)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_remove(self):
        tok = self.peek()
        self.expect("remove")
        if self.at("the", "last", "item", "from"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            name = self.expect_name("the name of the list")
            node = RemoveLast(name)
        elif self.peek().type == WORD and self.peek().value == "item":
            self.advance()
            index = self.expression()
            self.expect("from")
            name = self.expect_name("the name of the list")
            node = RemoveItem(index, name)
        else:
            raise self.syntax(
                "After the word remove on line %s I expected the words the last item, or the word item with a number." % tok.line,
                "Write Remove the last item from scores, or Remove item 2 from scores.")
        node.line = tok.line
        self.end_statement()
        return node

    def parse_sort(self):
        tok = self.peek()
        self.expect("sort")
        name = self.expect_name("the name of the list")
        node = SortList(name)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_reverse(self):
        tok = self.peek()
        self.expect("reverse")
        name = self.expect_name("the name of the list")
        node = ReverseList(name)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_function(self):
        tok = self.peek()
        self.expect("to")
        name = self.expect_name("the name of the function")
        params = []
        if self.accept("with"):
            params.append(self.expect_name("the name of the first input"))
            while self.accept("and"):
                params.append(self.expect_name("the name of the next input"))
        self.skip_commas()
        self.expect("do")
        self.func_depth += 1
        self.block_start_line = tok.line
        body = self.parse_block(("end", "function"))
        self.func_depth -= 1
        self.expect("end", "function")
        node = FunctionDef(name, params, body)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_run(self):
        tok = self.peek()
        self.expect("run")
        name = self.expect_name("the name of the function")
        args = []
        if self.accept("with"):
            args.append(self.parse_comparison(True))
            while self.accept("and"):
                args.append(self.parse_comparison(True))
        node = RunCall(name, args)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_try(self):
        tok = self.peek()
        self.expect("try")
        self.skip_commas()
        self.block_start_line = tok.line
        body = self.parse_block(("if", "something", "goes", "wrong"), ("end", "try"))
        handler = None
        if self.accept("if", "something", "goes", "wrong"):
            self.skip_commas()
            handler = self.parse_block(("end", "try"))
        self.expect("end", "try")
        node = TryBlock(body, handler)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_use(self):
        tok = self.peek()
        self.expect("use", "the", "file")
        tok2 = self.peek()
        if tok2.type != TEXT:
            raise self.syntax(
                "After the words use the file on line %s I expected a text literal with the file name." % tok.line,
                "Write it like: Use the file text helpers.pln end text.")
        self.advance()
        node = UseFile(tok2.value)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_wait(self):
        tok = self.peek()
        self.expect("wait")
        seconds = self.expression()
        self.expect("seconds")
        node = WaitStmt(seconds)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_give_back(self):
        tok = self.peek()
        self.expect("give", "back")
        if self.func_depth == 0:
            raise self.syntax(
                "The words give back on line %s are outside of any function." % tok.line,
                "give back can only be used inside a function, between do and end function.")
        value = self.expression()
        node = GiveBack(value)
        node.line = tok.line
        self.end_statement()
        return node

    def parse_stop(self):
        tok = self.peek()
        self.expect("stop", "the", "loop")
        if self.loop_depth == 0:
            raise self.syntax(
                "The words stop the loop on line %s are not inside any loop." % tok.line,
                "stop the loop can only be used inside Repeat, While, For each or Count loops.")
        node = StopLoop()
        node.line = tok.line
        self.end_statement()
        return node

    def parse_skip(self):
        tok = self.peek()
        self.expect("skip", "to", "the", "next", "one")
        if self.loop_depth == 0:
            raise self.syntax(
                "The words skip to the next one on line %s are not inside any loop." % tok.line,
                "skip to the next one can only be used inside Repeat, While, For each or Count loops.")
        node = SkipOne()
        node.line = tok.line
        self.end_statement()
        return node

    # --- expressions ----------------------------------------------------------

    def expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.accept("or"):
            right = self.parse_and()
            node = Or(left, right)
            node.line = left.line
            left = node
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.accept("and"):
            right = self.parse_not()
            node = And(left, right)
            node.line = left.line
            left = node
        return left

    def parse_not(self):
        if self.accept("not"):
            node = Not(self.parse_not())
            node.line = self.prev.line
            return node
        return self.parse_comparison()

    def parse_comparison(self, in_call_arg=False):
        left = self.parse_concat(in_call_arg)
        if self.at("is"):
            self.advance()
            if self.accept("not", "equal", "to"):
                op = "not_equal"
            elif self.accept("equal", "to"):
                op = "equal"
            elif self.accept("greater", "than"):
                op = "greater"
            elif self.accept("less", "than"):
                op = "less"
            elif self.accept("at", "least"):
                op = "at_least"
            elif self.accept("at", "most"):
                op = "at_most"
            else:
                tok = self.peek()
                raise self.syntax(
                    "After the word is on line %s I expected equal to, not equal to, greater than, less than, at least or at most." % tok.line,
                    "For example: score is greater than 5.")
            right = self.parse_concat(in_call_arg)
            node = Compare(op, left, right)
            node.line = left.line
            left = node
            if self.at("is"):
                tok = self.peek()
                raise self.syntax(
                    "I can only compare two things at a time on line %s." % tok.line,
                    "To compare step by step, wrap one comparison in the words group and end group.")
        elif self.accept("contains"):
            right = self.parse_concat(in_call_arg)
            node = Contains(left, right)
            node.line = left.line
            left = node
        return left

    def parse_concat(self, in_call_arg=False):
        left = self.parse_additive(in_call_arg)
        while self.accept("joined", "with"):
            right = self.parse_additive()
            node = Joined(left, right)
            node.line = left.line
            left = node
        return left

    def parse_additive(self, in_call_arg=False):
        left = self.parse_multiplicative()
        while True:
            # Inside function inputs, plus or minus followed by another call
            # ends this input and belongs to the enclosing expression.
            if in_call_arg and (self.at("plus", "the", "result") or self.at("minus", "the", "result")):
                return left
            if self.accept("plus"):
                right = self.parse_multiplicative()
                node = BinOp("plus", left, right)
            elif self.accept("minus"):
                right = self.parse_multiplicative()
                node = BinOp("minus", left, right)
            else:
                return left
            node.line = left.line
            left = node

    def parse_multiplicative(self):
        left = self.parse_power()
        while True:
            if self.accept("times"):
                right = self.parse_power()
                node = BinOp("times", left, right)
            elif self.accept("divided", "by"):
                right = self.parse_power()
                node = BinOp("divided", left, right)
            elif self.accept("remainder", "of"):
                right = self.parse_power()
                node = BinOp("remainder", left, right)
            else:
                return left
            node.line = left.line
            left = node

    def parse_power(self):
        base = self.parse_unary()
        if self.accept("to", "the", "power", "of"):
            exponent = self.parse_power()
            node = BinOp("power", base, exponent)
            node.line = base.line
            return node
        return base

    def parse_unary(self):
        tok = self.peek()
        if tok.type == WORD and tok.value == "negative":
            self.advance()
            node = Negative(self.parse_unary())
            node.line = tok.line
            return node
        if self.at("the", "square", "root", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = SquareRoot(self.parse_unary())
            node.line = tok.line
            return node
        if self.at("the", "absolute", "value", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = AbsoluteValue(self.parse_unary())
            node.line = tok.line
            return node
        if self.at("uppercase", "of"):
            self.advance()
            self.advance()
            node = UppercaseOf(self.parse_unary())
            node.line = tok.line
            return node
        if self.at("lowercase", "of"):
            self.advance()
            self.advance()
            node = LowercaseOf(self.parse_unary())
            node.line = tok.line
            return node
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        if self.accept("rounded"):
            wrapped = Rounded(node)
            wrapped.line = node.line
            node = wrapped
        return node

    def parse_primary(self):
        tok = self.peek()
        if tok.type == NUMBER:
            self.advance()
            value = tok.value
            if self.at("point") and self.peek(1).type == NUMBER:
                digits = str(self.peek(1).value)
                self.advance()
                self.advance()
                value = float("%s.%s" % (value, digits))
            node = Number(value)
            node.line = tok.line
            return node
        if tok.type == TEXT:
            self.advance()
            node = TextLiteral(tok.value)
            node.line = tok.line
            return node
        if tok.type != WORD:
            if tok.type == EOF:
                raise self.incomplete(
                    "The program ends in the middle of a statement that starts on line %s." % (self.prev.line if self.prev else tok.line))
            raise self.syntax(
                "I expected a value on line %s, but I found %s." % (tok.line, self.describe(tok)),
                "A value can be a number, a text literal, yes, no, nothing, or the name of a variable.")
        word = tok.value
        if word == "yes":
            self.advance()
            node = Bool(True)
            node.line = tok.line
            return node
        if word == "no":
            self.advance()
            node = Bool(False)
            node.line = tok.line
            return node
        if word == "nothing":
            self.advance()
            node = Nothing()
            node.line = tok.line
            return node
        if word == "group":
            self.advance()
            inner = self.expression()
            self.expect("end", "group")
            return inner
        if word == "item":
            return self.parse_item_of()
        if word == "the":
            return self.parse_the_phrase()
        if self.at("a", "list", "holding"):
            self.advance()
            self.advance()
            self.advance()
            items = [self.expression()]
            while self.peek().type == COMMA:
                self.advance()
                items.append(self.expression())
            node = ListLiteral(items)
            node.line = tok.line
            return node
        if self.at("random", "number", "from"):
            self.advance()
            self.advance()
            self.advance()
            start = self.parse_additive()
            self.expect("to")
            stop = self.parse_additive()
            node = RandomNumber(start, stop)
            node.line = tok.line
            return node
        if self.at("secure", "random", "number", "from"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            start = self.parse_additive()
            self.expect("to")
            stop = self.parse_additive()
            node = SecureRandom(start, stop)
            node.line = tok.line
            return node
        if word == "encrypt" or word == "decrypt":
            self.advance()
            value = self.parse_additive()
            self.expect("with")
            self.expect("key")
            key = self.parse_additive()
            if word == "encrypt":
                node = Encrypt(value, key)
            else:
                node = Decrypt(value, key)
            node.line = tok.line
            return node
        if word == "split":
            self.advance()
            value = self.parse_additive()
            self.expect("by")
            separator = self.parse_additive()
            node = SplitText(value, separator)
            node.line = tok.line
            return node
        if self.at("read", "file"):
            self.advance()
            self.advance()
            node = ReadFile(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("write", "file"):
            self.advance()
            self.advance()
            path = self.parse_postfix()
            self.expect("with")
            content = self.parse_additive()
            node = WriteFile(path, content)
            node.line = tok.line
            return node
        # a plain (possibly multi-word) name
        name = self.expect_name("a value")
        node = Var(name)
        node.line = tok.line
        return node

    def parse_item_of(self):
        tok = self.peek()
        save = self.pos
        self.advance()
        try:
            index = self.parse_additive()
        except PlainError:
            self.pos = save
            self.advance()
            node = Var("item")
            node.line = tok.line
            return node
        if self.at("of"):
            self.advance()
            container = self.parse_postfix()
            node = ItemOf(index, container)
            node.line = tok.line
            return node
        self.pos = save
        self.advance()
        node = Var("item")
        node.line = tok.line
        return node

    def parse_the_phrase(self):
        tok = self.peek()
        if self.at("the", "length", "of"):
            self.advance()
            self.advance()
            self.advance()
            node = LengthOf(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "larger", "of"):
            self.advance()
            self.advance()
            self.advance()
            left = self.parse_comparison()
            self.expect("and")
            right = self.parse_comparison()
            node = LargerOf(left, right)
            node.line = tok.line
            return node
        if self.at("the", "smaller", "of"):
            self.advance()
            self.advance()
            self.advance()
            left = self.parse_comparison()
            self.expect("and")
            right = self.parse_comparison()
            node = SmallerOf(left, right)
            node.line = tok.line
            return node
        if self.at("the", "first", "item", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = FirstItemOf(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "last", "item", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = LastItemOf(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "result", "of"):
            self.advance()
            self.advance()
            self.advance()
            name = self.expect_name("the name of the function")
            args = []
            if self.accept("with"):
                args.append(self.parse_comparison(True))
                while self.accept("and"):
                    args.append(self.parse_comparison(True))
            node = Call(name, args)
            node.line = tok.line
            return node
        if self.at("the", "secure", "hash", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = SecureHash(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "number", "version", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = ToNumber(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "text", "version", "of"):
            self.advance()
            self.advance()
            self.advance()
            self.advance()
            node = ToText(self.parse_postfix())
            node.line = tok.line
            return node
        if self.at("the", "current", "time"):
            self.advance()
            self.advance()
            self.advance()
            node = CurrentTime()
            node.line = tok.line
            return node
        if self.at("the", "problem"):
            self.advance()
            self.advance()
            node = TheProblem()
            node.line = tok.line
            return node
        raise self.syntax(
            "I do not know this use of the word the on line %s." % tok.line,
            "The word the is used in phrases like the length of, the larger of, the first item of, the result of, the current time and the problem.")

    def parse_expression_only(self):
        node = self.expression()
        tok = self.peek()
        if tok.type != EOF:
            raise self.syntax(
                "I found %s after the end of an expression on line %s." % (self.describe(tok), tok.line),
                "Try wrapping the part you want in the words group and end group.")
        return node
