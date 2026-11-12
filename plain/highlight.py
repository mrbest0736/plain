"""Colour coding for Plain source code.

Turns .pln source into ANSI-coloured text for the terminal.  The scanner is
regex based and mirrors the editor grammar in
editors/plain-vscode/syntaxes/plain.tmLanguage.json so the terminal and the
editor agree on what is what.  Categories, in the order they are tried:

1. text literals   -- text ... end text (green).  "the text version of" is
                      not a literal opener, so it is excluded here and
                      coloured as a phrase below.
2. comments        -- Note ... end note (grey).  Anything after Note on a
                      line stays grey, and an unterminated comment greys out
                      the rest of the line.
3. numbers         -- digits, decimals with point, negative (yellow).
4. end phrases     -- end if, end loop, end function, ... (bold cyan).
5. the-phrases     -- the length of, the square root of, the secure hash of,
                      ... (bold blue).
6. keywords        -- every reserved word (bold cyan); yes/no/nothing are
                      constants (magenta).
7. punctuation     -- commas and periods (dim).
8. forbidden       -- any symbol that is not a comma or period (bold red),
                      so illegal punctuation is visible at a glance.
"""

import re

RESET = "\x1b[0m"
COMMENT = "\x1b[90m"
TEXT = "\x1b[32m"
NUMBER = "\x1b[33m"
CONSTANT = "\x1b[35m"
KEYWORD = "\x1b[1;36m"
PHRASE = "\x1b[1;34m"
PUNCT = "\x1b[2m"
FORBIDDEN = "\x1b[1;31m"

from plain.lexer import RESERVED  # noqa: E402

THE_PHRASES = (
    "square root of", "absolute value of", "larger of", "smaller of",
    "length of", "first item of", "last item of", "result of",
    "text version of", "number version of", "current time", "problem",
    "secure hash of",
)

OPERATOR_WORDS = (
    "plus", "minus", "divided", "remainder", "rounded", "joined",
    "contains", "is",
)

TOKEN_RE = re.compile(
    r"""
      (?P<text>\btext\b(?!\s*version\s+of\b).*?\bend\s+text\b
        |\btext\b(?!\s*version\s+of\b).*\Z)
    | (?P<comment>\bnote\b.*?\bend\s+note\b|\bnote\b.*\Z)
    | (?P<number>\bnegative\b(?=\s+\d)|\b\d+(?:\s+point\s+\d+)?\b)
    | (?P<end_phrase>\bend\s+(?:if|loop|function|try|text|note|group)\b)
    | (?P<phrase>\bthe\s+(?:%s)\b)
    | (?P<word>[A-Za-z]+)
    | (?P<comma>,)
    | (?P<period>\.)
    | (?P<forbidden>[^\w\s,.])
    """ % "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in THE_PHRASES),
    re.VERBOSE | re.IGNORECASE | re.DOTALL,
)


def _wrap(text, colour):
    return "%s%s%s" % (colour, text, RESET)


def highlight_line(line):
    """Return one source line with ANSI colour codes added."""
    out = []
    pos = 0
    for m in TOKEN_RE.finditer(line):
        if m.start() > pos:
            out.append(line[pos:m.start()])
        kind = m.lastgroup
        piece = m.group()
        if kind == "text":
            out.append(_wrap(piece, TEXT))
        elif kind == "comment":
            out.append(_wrap(piece, COMMENT))
        elif kind == "number":
            out.append(_wrap(piece, NUMBER))
        elif kind == "end_phrase":
            out.append(_wrap(piece, KEYWORD))
        elif kind == "phrase":
            out.append(_wrap(piece, PHRASE))
        elif kind == "word":
            low = piece.lower()
            if low in ("yes", "no", "nothing"):
                out.append(_wrap(piece, CONSTANT))
            elif low in RESERVED:
                out.append(_wrap(piece, KEYWORD))
            else:
                out.append(piece)
        elif kind == "comma":
            out.append(_wrap(piece, PUNCT))
        elif kind == "period":
            out.append(_wrap(piece, PUNCT))
        else:
            out.append(_wrap(piece, FORBIDDEN))
        pos = m.end()
    out.append(line[pos:])
    return "".join(out)


def highlight_source(source):
    """Return a whole program with every line colour coded."""
    return "\n".join(highlight_line(line) for line in source.split("\n"))


def highlight_file(path):
    """Read a .pln file and return its colour-coded source."""
    with open(path, "r", encoding="utf-8") as handle:
        return highlight_source(handle.read())
