"""Tests for the terminal colour coder in plain/highlight.py."""

from plain.highlight import (
    COMMENT, CONSTANT, FORBIDDEN, KEYWORD, NUMBER, PHRASE, RESET, TEXT,
    highlight_line, highlight_source,
)


def codes(line):
    return highlight_line(line)


def test_keywords_are_coloured():
    out = codes("Say text hi end text.")
    assert KEYWORD + "Say" + RESET in out


def test_text_literal_is_green():
    out = codes("Say text Hello, world. end text")
    assert TEXT + "text Hello, world. end text" + RESET in out


def test_comment_is_grey():
    out = codes("Note this explains things end note.")
    assert COMMENT + "Note this explains things end note" + RESET in out


def test_numbers_are_yellow():
    out = codes("Set x to 3 point 14.")
    assert NUMBER + "3 point 14" + RESET in out


def test_negative_is_yellow():
    out = codes("Set x to negative 5.")
    assert NUMBER + "negative" + RESET in out


def test_yes_no_nothing_are_constants():
    for word in ("yes", "no", "nothing"):
        out = codes("Set x to %s." % word)
        assert CONSTANT + word + RESET in out


def test_end_phrases_are_keywords():
    out = codes("end if.")
    assert KEYWORD + "end if" + RESET in out


def test_the_phrases_are_coloured():
    out = codes("Set x to the secure hash of name.")
    assert PHRASE + "the secure hash of" + RESET in out


def test_text_version_of_is_not_a_literal():
    out = codes("Say the text version of 42.")
    assert TEXT not in out
    assert PHRASE + "the text version of" + RESET in out


def test_forbidden_symbols_are_red():
    out = codes("Set bad to 5 + 3.")
    assert FORBIDDEN + "+" + RESET in out


def test_forbidden_bracket_is_red():
    out = codes("Set bad to 5 [ 3.")
    assert FORBIDDEN + "[" + RESET in out


def test_plain_words_untouched():
    out = codes("Set total score to 10.")
    assert "total score" in out
    assert "10" not in out or NUMBER in out


def test_case_insensitive_keywords():
    out = codes("SAY text hi end text.")
    assert KEYWORD + "SAY" + RESET in out


def test_words_inside_text_literal_not_keyword_coloured():
    out = codes("Say text set if while end text")
    assert KEYWORD + "set" + RESET not in out


def test_highlight_source_joins_lines():
    source = "Say text one end text.\nSay text two end text.\n"
    out = highlight_source(source)
    assert out.count("\n") == 2
    assert TEXT in out
