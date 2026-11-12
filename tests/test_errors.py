import pytest

from plain.errors import PlainSyntaxError, PlainRuntimeError
from plain.lexer import lex
from plain.parser import Parser

from conftest import run_src, run_error, lex_error


class TestForbiddenSymbolMessages:
    def test_plus_sign_exact_message(self):
        src = "Set a to 1.\nSet b to 2.\nSet c to 3.\nSet d to 4 + 2."
        error = lex_error(src)
        text = str(error)
        assert "I found a plus sign on line 4." in text
        assert "Use the word plus instead." in text

    def test_minus_sign(self):
        text = str(lex_error("Set x to 5 - 3."))
        assert "I found a minus sign on line 1." in text
        assert "Use the word minus instead" in text

    def test_equals_sign_explains_both_options(self):
        text = str(lex_error("x = 5."))
        assert "is equal to" in text
        assert "Set" in text

    def test_error_quotes_the_offending_line(self):
        src = "Set a to 1.\nSet b to 2 * 3."
        text = str(lex_error(src))
        assert "Set b to 2 * 3." in text
        assert "on line 2" in text


class TestSyntaxErrorMessages:
    def test_missing_period_names_line(self):
        src = "Set alpha to 1.\nSet beta to 2"
        with pytest.raises(PlainSyntaxError) as exc:
            Parser(lex(src), src).parse_program()
        text = str(exc.value)
        assert "period" in text
        assert "line 2" in text

    def test_unknown_statement_word(self):
        src = "Set alpha to 1.\nFrobnicate alpha."
        with pytest.raises(PlainSyntaxError) as exc:
            Parser(lex(src), src).parse_program()
        assert "Frobnicate" in str(exc.value)
        assert "line 2" in str(exc.value)

    def test_give_back_outside_function(self):
        with pytest.raises(PlainSyntaxError) as exc:
            Parser(lex("give back 5."), "give back 5.").parse_program()
        assert "inside a function" in str(exc.value)

    def test_stop_outside_loop(self):
        with pytest.raises(PlainSyntaxError) as exc:
            Parser(lex("Stop the loop."), "Stop the loop.").parse_program()
        assert "inside" in str(exc.value) and "loop" in str(exc.value)


class TestRuntimeErrorMessages:
    def test_undefined_variable(self):
        src = "Set alpha to 1.\nSay beta."
        error = run_error(src)
        text = str(error)
        assert "runtime problem" in text
        assert "line 2" in text
        assert "Say beta." in text
        assert "Set beta to" in text

    def test_divide_by_zero(self):
        src = "Set total to 10 divided by 0."
        error = run_error(src)
        text = str(error)
        assert "zero" in text.lower()
        assert "line 1" in text

    def test_bad_condition(self):
        src = "Set x to 5.\nIf x, then Say text hi end text. end if."
        error = run_error(src)
        assert "yes or no" in str(error)

    def test_item_out_of_range(self):
        src = "Make a list called s holding 1, 2.\nSay item 5 of s."
        error = run_error(src)
        text = str(error)
        assert "item 5" in text
        assert "2 items" in text

    def test_wrong_argument_count(self):
        src = ("To f with value, do give back value. end function.\n"
               "Run f with 1 and 2.")
        error = run_error(src)
        assert "expects 1 input" in str(error)

    def test_undefined_function(self):
        src = "Set alpha to 1.\nRun mystery with 2."
        error = run_error(src)
        assert "mystery" in str(error)
        assert "line 2" in str(error)


class TestErrorRendering:
    def test_render_has_three_parts(self):
        src = "Set alpha to 1.\nSay beta."
        error = run_error(src)
        lines = str(error).splitlines()
        assert lines[0].startswith("I found a runtime problem on line 2")
        assert lines[1].strip() == "Say beta."
        assert len(lines) >= 3