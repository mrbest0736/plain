"""Differential tests: the compiled runner (plain.vm.Runtime) must behave
exactly like the reference tree-walking interpreter (plain.interpreter).

Every snippet is run through both engines with the same inputs; stdout and any
error message must match character for character.
"""

import io

import pytest

from plain import builtins
from plain.errors import PlainError, PlainRuntimeError
from plain.interpreter import Interpreter
from plain.lexer import lex
from plain.parser import Parser
from plain.vm import Runtime


def run_with(engine_class, src, inputs, filename=None):
    out = io.StringIO()
    pending = list(inputs or [])

    def input_fn():
        if not pending:
            raise EOFError
        return pending.pop(0)

    engine = engine_class(source=src, filename=filename, output=out.write, input_fn=input_fn)
    program = Parser(lex(src), src).parse_program()
    engine.run(program)
    return out.getvalue()


def run_both(src, inputs=None, filename=None):
    builtins._random.seed(1234)
    tree_out = run_with(Interpreter, src, inputs, filename)
    builtins._random.seed(1234)
    vm_out = run_with(Runtime, src, inputs, filename)
    assert vm_out == tree_out
    return vm_out


def error_both(src, inputs=None, filename=None):
    builtins._random.seed(1234)
    with pytest.raises(PlainError) as tree_exc:
        run_with(Interpreter, src, inputs, filename)
    builtins._random.seed(1234)
    with pytest.raises(PlainError) as vm_exc:
        run_with(Runtime, src, inputs, filename)
    assert str(vm_exc.value) == str(tree_exc.value)
    return vm_exc.value


CORPUS = [
    # variables and math
    ("Set score to 10.\nChange score by 5.\nSay score.", "15\n"),
    ("Say 2 plus 3 times 4.", "14\n"),
    ("Say group 2 plus 3 end group times 4.", "20\n"),
    ("Say 2 to the power of 3 to the power of 2.", "512\n"),
    ("Say negative 5 plus 1.", "-4\n"),
    ("Say 3 point 5 plus 0 point 5.", "4\n"),
    ("Say 7 divided by 2.", "3.5\n"),
    ("Say 7 remainder of 3.", "1\n"),
    ("Say the square root of 16.", "4\n"),
    ("Say the absolute value of negative 8.", "8\n"),
    ("Say 2 point 7 rounded.", "3\n"),
    ("Say the larger of 3 and 9.", "9\n"),
    ("Say the smaller of text a end text and text b end text.", "a\n"),
    # text
    ("Say text Hello end text joined with text  world end text.", "Hello world\n"),
    ("Say the length of text hello end text.", "5\n"),
    ("Say uppercase of text hi end text.", "HI\n"),
    ("Say lowercase of text HI end text.", "hi\n"),
    ("Say the text version of 42.", "42\n"),
    ("Say the number version of text 3 point 5 end text.", "3.5\n"),
    ("If text hello end text contains text ell end text, then Say text yes end text. end if.", "yes\n"),
    # conditions
    ("If 5 is greater than 3, then Say text big end text. otherwise Say text small end text. end if.", "big\n"),
    ("If 5 is less than 3, then Say text big end text. otherwise if 5 is equal to 5, then Say text five end text. otherwise Say text small end text. end if.", "five\n"),
    ("If not no, then Say text yes end text. end if.", "yes\n"),
    ("If 1 is equal to 1 and 2 is equal to 2, then Say text both end text. end if.", "both\n"),
    ("If 1 is equal to 2 or 2 is equal to 2, then Say text either end text. end if.", "either\n"),
    ("If 1 is not equal to 2, then Say text different end text. end if.", "different\n"),
    ("If 5 is at least 5 and 5 is at most 5, then Say text edge end text. end if.", "edge\n"),
    # loops
    ("Set total to 0.\nRepeat 4 times, Change total by 2. end loop.\nSay total.", "8\n"),
    ("Count from 1 to 5 using i, Say i. end loop.", "1\n2\n3\n4\n5\n"),
    ("Count from 1 to 9 using i by 3, Say i. end loop.", "1\n4\n7\n"),
    ("Set n to 0.\nWhile n is less than 3, Change n by 1. end loop.\nSay n.", "3\n"),
    ("Repeat 5 times, Say text once end text. Stop the loop. end loop.", "once\n"),
    ("Count from 1 to 4 using i, If i is equal to 2, then Skip to the next one. end if. Say i. end loop.", "1\n3\n4\n"),
    # lists
    ("Make a list called scores holding 5, 10, 15.\nSay item 2 of scores.", "10\n"),
    ("Make a list called scores holding 5, 10.\nSet item 2 of scores to 99.\nSay item 2 of scores.", "99\n"),
    ("Make a list called scores holding 3, 1, 2.\nSort scores.\nSay scores.", "[1, 2, 3]\n"),
    ("Make a list called scores holding 1, 2, 3.\nReverse scores.\nSay scores.", "[3, 2, 1]\n"),
    ("Make a list called scores holding 1, 2.\nAdd 3 to scores.\nSay the last item of scores.", "3\n"),
    ("Make a list called scores holding 1, 2, 3.\nRemove the last item from scores.\nSay the length of scores.", "2\n"),
    ("Make a list called scores holding 1, 2, 3.\nRemove item 2 from scores.\nSay scores.", "[1, 3]\n"),
    ("Make a list called scores holding 1, 2, 3.\nSay the first item of scores.", "1\n"),
    ("Make a list called scores holding 1, 2.\nIf scores contains 2, then Say text found end text. end if.", "found\n"),
    ("Make a list called grid holding a list holding 1, 2, a list holding 3, 4.\nSay item 2 of item 1 of grid.", "2\n"),
    ("Say a list holding 1, a list holding 2, 3.", "[1, [2, 3]]\n"),
    # functions
    ("To add numbers with first and second, do give back first plus second. end function.\nSay the result of add numbers with 3 and 4.", "7\n"),
    ("To greet with name, do Say text hi end text, name. end function.\nRun greet with text Ada end text.", "hi Ada\n"),
    ("Set counter to 0.\nTo bump, do Change counter by 1. end function.\nRun bump. Run bump.\nSay counter.", "2\n"),
    ("To fib with n, do If n is less than 2, then give back n. end if. give back group the result of fib with n minus 1 end group plus group the result of fib with n minus 2 end group. end function.\nSay the result of fib with 10.", "55\n"),
    ("To f with value, do Say value. end function.\nRun f with 1.", "1\n"),
    ("Set x to 1.\nTo look x, do give back x. end function.\nSet x to 2.\nSay the result of look x.", "2\n"),
    ("To f, do give back nothing. end function.\nSay the result of f.", "nothing\n"),
    ("Set outer to text global end text.\nTo f, do Set inner to text local end text. Say outer, inner. end function.\nRun f.", "global local\n"),
    # try / catch
    ("Try, Say 1 divided by 0. if something goes wrong, Say text caught end text. end try.\nSay text after end text.", "caught\nafter\n"),
    ("Try, Say 1 divided by 0. if something goes wrong, Say the problem. end try.", "I tried to divide 1 by zero on line 1.\n"),
    ("Try, Say text fine end text. if something goes wrong, Say text caught end text. end try.", "fine\n"),
    ("Try, Say 1 divided by 0. end try.\nSay text kept going end text.", "kept going\n"),
    # say / write / nothing / yes no
    ("Say text a end text, 1, yes, nothing.", "a 1 yes nothing\n"),
    ("Write text a end text. Write 1. Say text b end text.", "a1b\n"),
    ("Set empty to nothing.\nSay empty.", "nothing\n"),
    # multi-word names and case
    ("Set TOTAL SCORE to 9.\nchange total score by 1.\nSay total score.", "10\n"),
    # builtins
    ("Split text a,b,c end text by text , end text.\n", None),  # placeholder replaced below
]
CORPUS = [entry for entry in CORPUS if entry[1] is not None]
CORPUS.append((
    "Make a list called parts holding split text a,b end text by text , end text.\nSay item 1 of parts.",
    "[a, b]\n",
))
CORPUS.append((
    "Make a list called parts holding split text a,b end text by text , end text.\nSay the first item of the first item of parts.",
    "a\n",
))
CORPUS.append((
    "Set n to 0.\nRepeat 3 times, Change n by 1. end loop.\nSay the text version of n joined with text ok end text.",
    "3ok\n",
))

ERROR_CORPUS = [
    'Say mystery name.',
    'Say 1 plus text a end text.',
    'Say 1 divided by 0.',
    'Say item 9 of a list holding 1.',
    'Change ghost by 1.',
    'Set x to 1.\nChange x by text a end text.',
    'If 3, then Say text x end text. end if.',
    'Say the problem.',
    'To f with value, do give back value. end function.\nRun f with 1 and 2.',
    'Run nosuch with 1.',
    'Say the length of 5.',
    'Say uppercase of 5.',
    'Say negative text a end text.',
    'For each thing in 5, Say thing. end loop.',
    'Repeat 2 point 5 times, Say text x end text. end loop.',
    'Make a list called l holding 1, text a end text.\nSort l.',
    'Say 0 to the power of negative 1.',
    'Say text a end text contains 5.',
    'Make a list called l holding 1.\nRemove the last item from l.\nRemove the last item from l.',
]

class TestSameOutput:
    @pytest.mark.parametrize("src,expected", CORPUS)
    def test_matches_reference(self, src, expected):
        assert run_both(src) == expected

    def test_input_program(self):
        src = "Ask the user for name.\nSay text hi end text, name.\nAsk the user for a number called age.\nSay age plus 1."
        assert run_both(src, ["Ada", "20"]) == "hi Ada\n21\n"

    def test_bad_number_reasks(self):
        src = "Ask the user for a number called age.\nSay age."
        assert run_both(src, ["nope", "7"]) == "That is not a number. Please type something like 42.\n7\n"

    def test_read_write_file(self, tmp_path):
        src = ("Write file text notes.txt end text with text hello file end text. "
               "Say read file text notes.txt end text.")
        main = str(tmp_path / "main.pln")
        assert run_both(src, [], filename=main) == "hello file\n"
        assert (tmp_path / "notes.txt").read_text() == "hello file"


class TestSameErrors:
    @pytest.mark.parametrize("src", ERROR_CORPUS)
    def test_error_messages_match(self, src):
        error = error_both(src)
        assert isinstance(error, PlainRuntimeError)

    def test_error_quotes_line(self):
        error = error_both("Set alpha to 1.\nSay beta.")
        assert "line 2" in str(error)
        assert "Say beta." in str(error)
