import pytest

from plain.lexer import lex, WORD, NUMBER, TEXT, COMMA, PERIOD, EOF, RESERVED
from plain.errors import PlainSyntaxError, PlainIncomplete

from conftest import lex_error


def types(src):
    return [t.type for t in lex(src)]


def values(src):
    return [t.value for t in lex(src)]


class TestBasicTokens:
    def test_words(self):
        tokens = lex("Set score to 10.")
        assert [t.value for t in tokens] == ["set", "score", "to", 10, ".", None]
        assert [t.type for t in tokens] == [WORD, WORD, WORD, NUMBER, PERIOD, EOF]

    def test_case_insensitive(self):
        tokens = lex("SET Score TO 10.")
        assert [t.value for t in tokens] == ["set", "score", "to", 10, ".", None]

    def test_commas_and_periods(self):
        tokens = lex("Say a, b.")
        assert [t.type for t in tokens] == [WORD, WORD, COMMA, WORD, PERIOD, EOF]

    def test_number_token(self):
        tokens = lex("42")
        assert tokens[0].type == NUMBER
        assert tokens[0].value == 42

    def test_decimal_is_number_word_number(self):
        tokens = lex("3 point 14")
        assert [t.type for t in tokens] == [NUMBER, WORD, NUMBER, EOF]
        assert [t.value for t in tokens] == [3, "point", 14, None]

    def test_lines_are_tracked(self):
        tokens = lex("Set a to 1.\nSet b to 2.\n\nSet c to 3.")
        assert tokens[0].line == 1
        assert tokens[5].line == 2
        assert tokens[-2].line == 4


class TestTextLiterals:
    def test_simple(self):
        tokens = lex("text hello end text")
        assert tokens[0].type == TEXT
        assert tokens[0].value == "hello"

    def test_commas_and_periods_inside(self):
        tokens = lex("text Hello, world. end text")
        assert tokens[0].value == "Hello, world."

    def test_empty_literal(self):
        tokens = lex("text end text")
        assert tokens[0].value == ""

    def test_single_space_literal(self):
        tokens = lex("text   end text")
        assert tokens[0].value == " "

    def test_multiple_spaces_before_end(self):
        tokens = lex("text a  end text")
        assert tokens[0].value == "a "

    def test_multiline_literal(self):
        tokens = lex("text one\ntwo end text")
        assert tokens[0].value == "one\ntwo"
        assert lex("text one\ntwo end text")[1].line == 2

    def test_symbols_allowed_inside(self):
        tokens = lex("text (a) + b end text")
        assert tokens[0].value == "(a) + b"

    def test_unclosed_is_incomplete(self):
        with pytest.raises(PlainIncomplete):
            lex("Say text hello")

    def test_word_containing_text_is_not_literal(self):
        tokens = lex("Say textbook.")
        assert tokens[1].type == WORD
        assert tokens[1].value == "textbook"


class TestNotes:
    def test_note_skipped(self):
        tokens = lex("Note this adds things up end note. Set a to 1.")
        assert [t.value for t in tokens] == ["set", "a", "to", 1, ".", None]

    def test_note_without_trailing_period(self):
        tokens = lex("Set a to 1. Note a comment end note")
        assert [t.value for t in tokens] == ["set", "a", "to", 1, ".", None]

    def test_multiline_note(self):
        tokens = lex("Note one\ntwo\nthree end note. Set a to 1.")
        assert tokens[0].value == "set"

    def test_note_can_hold_symbols(self):
        tokens = lex("Note to-do: (stuff) + more end note. Set a to 1.")
        assert tokens[0].value == "set"

    def test_note_can_hold_the_word_text(self):
        tokens = lex("Note the text literal holds a space end note. Set a to 1.")
        assert tokens[0].value == "set"

    def test_unclosed_note_is_incomplete(self):
        with pytest.raises(PlainIncomplete):
            lex("Set a to 1. Note oops")


class TestForbiddenSymbols:
    def test_plus_sign(self):
        error = lex_error("Set x to 5 + 3.")
        assert isinstance(error, PlainSyntaxError)
        message = str(error)
        assert "I found a plus sign on line 1." in message
        assert "Use the word plus instead." in message

    def test_each_forbidden_symbol_is_rejected(self):
        cases = {
            "+": "plus", "-": "minus", "*": "times", "/": "divided by",
            "=": "is equal to", "<": "is less than", ">": "is greater than",
            "!": "not", "%": "remainder of", "^": "to the power of",
            "&": "and", "|": "or", "_": "a space",
        }
        for symbol, word in cases.items():
            error = lex_error("Set x to 5 %s 3." % symbol)
            assert isinstance(error, PlainSyntaxError), symbol
            assert "on line 1." in str(error), symbol

    def test_parentheses_suggest_group(self):
        error = lex_error("Say ( 1 plus 2 ) times 3.")
        assert "group" in str(error)

    def test_quotes_suggest_text(self):
        error = lex_error('Say "hello".')
        assert "text" in str(error)

    def test_error_names_the_line(self):
        error = lex_error("Set a to 1.\nSet b to 2.\nSet c to 3.\nSet d to 4 * 2.")
        assert "on line 4." in str(error)

    def test_underscore_suggestion(self):
        error = lex_error("Set total_score to 1.")
        assert "underscore" in str(error)


class TestDigitRules:
    def test_digits_inside_name_rejected(self):
        error = lex_error("Set score2 to 1.")
        assert "digit" in str(error)

    def test_word_right_after_number_rejected(self):
        error = lex_error("Say 12apples.")
        assert "space" in str(error)


class TestReservedWords:
    def test_reserved_list_contents(self):
        for word in ("set", "if", "then", "end", "text", "is", "plus", "yes", "no", "nothing"):
            assert word in RESERVED

    def test_common_nouns_are_not_reserved(self):
        for word in ("number", "list", "first", "last", "time", "add", "count"):
            assert word not in RESERVED
