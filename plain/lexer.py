"""The Plain lexer.

Plain source code may only contain letters, digits, spaces, commas and
periods.  Everything else is spelled out as words.  The lexer turns the
raw characters into five kinds of tokens:

    WORD    a single English word (lower-cased in .value, original in .text)
    NUMBER  a run of digits, e.g. 42
    TEXT    the inside of a text  ...  end text literal
    COMMA   ,
    PERIOD  .
    EOF     end of source

Comments (Note ... end note) are consumed here, and so are the rules
about which symbols are forbidden.
"""

from plain.errors import PlainSyntaxError, PlainIncomplete

WORD = "WORD"
NUMBER = "NUMBER"
TEXT = "TEXT"
COMMA = "COMMA"
PERIOD = "PERIOD"
EOF = "EOF"


class Token:
    __slots__ = ("type", "value", "text", "line", "col")

    def __init__(self, type_, value, text, line, col):
        self.type = type_
        self.value = value
        self.text = text
        self.line = line
        self.col = col

    def __repr__(self):
        return "Token(%s, %r, line %s)" % (self.type, self.value, self.line)


# Words that can follow a name or value, plus operator and literal words,
# must never be swallowed into a multi-word name.  They are reserved.
# A few words are special only in certain positions and ARE allowed inside
# names (see LANGUAGE_GUIDE.md): add, count, number, list, first, last,
# time, seconds, file, random, current, version, result, length, larger,
# smaller, square, root, absolute, value, uppercase, lowercase, equal,
# greater, less, than, at, least, most, one, next, something, goes, wrong,
# user, point, called is reserved but add/count/list/number are not.
RESERVED = {
    # statements
    "set", "change", "say", "write", "ask", "make", "remove", "sort",
    "reverse", "run", "try", "use", "wait", "give", "back", "stop", "skip",
    # control flow
    "if", "then", "otherwise", "end", "while", "repeat", "for", "each",
    "in", "from", "using", "function", "do", "loop", "times", "note",
    # small phrase words
    "the", "a", "of", "to", "by", "with", "holding", "called", "item",
    # literals and prefix words
    "text", "group", "yes", "no", "nothing", "not", "negative",
    # operators
    "and", "or", "plus", "minus", "divided", "remainder", "is",
    "contains", "joined", "rounded", "split", "read",
    # security
    "encrypt", "decrypt", "secure",
    # special
    "problem",
}

# Friendly names and fixes for forbidden symbols.
SYMBOL_SUGGESTIONS = {
    "+": ("plus sign", "Use the word plus instead."),
    "-": ("minus sign", "Use the word minus instead, or the word negative for negative numbers."),
    "*": ("times sign", "Use the word times instead."),
    "/": ("slash", "Use the words divided by instead."),
    "(": ("opening parenthesis", "Plain does not use parentheses. Use the words group and end group to control order."),
    ")": ("closing parenthesis", "Plain does not use parentheses. Use the words group and end group to control order."),
    "[": ("opening bracket", "Plain does not use brackets. Use make a list called things holding 1, 2, 3 to build a list."),
    "]": ("closing bracket", "Plain does not use brackets. Use make a list called things holding 1, 2, 3 to build a list."),
    "{": ("opening brace", "Plain does not use braces. Use the words if, loop and function to group code."),
    "}": ("closing brace", "Plain does not use braces. Use the words if, loop and function to group code."),
    "=": ("equals sign", "To compare two values use the words is equal to. To store a value use Set, like Set score to 10."),
    "<": ("less-than sign", "Use the words is less than instead."),
    ">": ("greater-than sign", "Use the words is greater than instead."),
    "!": ("exclamation mark", "Use the word not to reverse a yes or no."),
    '"': ("quotation mark", "Plain writes text with words: text like this end text."),
    "'": ("apostrophe", "Plain writes text with words: text like this end text."),
    ":": ("colon", "Plain uses periods and commas instead of colons."),
    ";": ("semicolon", "Plain ends statements with a period."),
    "&": ("ampersand", "Use the word and instead."),
    "|": ("pipe", "Use the word or instead."),
    "%": ("percent sign", "Use the words remainder of instead."),
    "^": ("caret", "Use the words to the power of instead."),
    "_": ("underscore", "Names in Plain use letters only. Write total score instead of total_score."),
    "#": ("hash sign", "Comments in Plain start with the word Note and end with end note."),
    "@": ("at sign", "Plain only uses letters, digits, spaces, commas and periods."),
    "$": ("dollar sign", "Plain only uses letters, digits, spaces, commas and periods."),
    "~": ("tilde", "Plain only uses letters, digits, spaces, commas and periods."),
    "`": ("backtick", "Plain only uses letters, digits, spaces, commas and periods."),
}
GENERIC_SUGGESTION = "Plain only uses letters, digits, spaces, commas and periods."


def _is_word_char(ch):
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def _match_word(src, i, word):
    """Return True if the exact word `word` starts at i and is bounded."""
    n = len(word)
    if src[i:i + n].lower() != word:
        return False
    after = i + n
    if after < len(src) and (_is_word_char(src[after]) or src[after].isdigit()):
        return False
    return True


def lex(source):
    """Turn Plain source text into a list of tokens ending with EOF."""
    tokens = []
    src = source
    n = len(src)
    i = 0
    line = 1
    col = 1

    def advance(k=1):
        nonlocal i, line, col
        for _ in range(k):
            if i < n and src[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1

    def syntax(problem, fix, at_line=None):
        return PlainSyntaxError(problem, fix, line=at_line if at_line is not None else line, source=source)

    def read_text_literal(start_line, start_col=0):
        """Read a text ... end text literal. Returns (content, token)."""
        nonlocal i, line, col
        advance(len("text"))  # past the word "text"
        if i >= n:
            raise PlainIncomplete(
                "The text starting on line %s never ends. Finish it with the words end text." % start_line)
        if not src[i].isspace():
            raise syntax(
                "I expected a space after the word text on line %s." % start_line,
                "Write text literals like: text hello end text")
        advance()  # exactly one space after "text"
        content_start = i
        if _match_word(src, i, "end text"):
            content = ""
            advance(len("end text"))
            return "", Token(TEXT, "", "", start_line, start_col)
        k = i
        while k < n:
            if src[k].isspace() and _match_word(src, k + 1, "end text"):
                content = src[content_start:k]
                advance(k - i)  # up to the whitespace before "end text"
                advance(len("end text") + 1)  # past that whitespace and "end text"
                return content, Token(TEXT, content, content, start_line, start_col)
            k += 1
        raise PlainIncomplete(
            "The text starting on line %s never ends. Finish it with the words end text." % start_line)

    def skip_note(start_line):
        """Skip a Note ... end note comment, including a trailing period."""
        nonlocal i
        advance(len("note"))  # past the word "note"
        while True:
            while i < n and src[i].isspace():
                advance()
            if i >= n:
                raise PlainIncomplete(
                    "The note starting on line %s never ends. Finish it with the words end note." % start_line)
            if _match_word(src, i, "end"):
                j = i + 3
                while j < n and src[j].isspace():
                    j += 1
                if _match_word(src, j, "note"):
                    advance(j - i)
                    advance(len("note"))
                    if i < n and src[i] == ".":
                        advance()
                    return
            if _is_word_char(src[i]):
                while i < n and _is_word_char(src[i]):
                    advance()
            else:
                # notes are prose: any symbol is allowed inside them
                advance()

    while i < n:
        ch = src[i]
        if ch == "\n":
            advance()
            continue
        if ch.isspace():
            advance()
            continue
        if ch == ",":
            tokens.append(Token(COMMA, ",", ",", line, col))
            advance()
            continue
        if ch == ".":
            tokens.append(Token(PERIOD, ".", ".", line, col))
            advance()
            continue
        if ch.isdigit():
            start_line, start_col = line, col
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j < n and _is_word_char(src[j]):
                bad = src[j]
                k = j
                while k < n and _is_word_char(src[k]):
                    k += 1
                raise syntax(
                    "I found the word %s right after the number %s on line %s." % (src[j:k], src[i:j], line),
                    "Put a space between the number and the word.")
            value = int(src[i:j])
            tokens.append(Token(NUMBER, value, src[i:j], start_line, start_col))
            advance(j - i)
            continue
        if _is_word_char(ch):
            start_line, start_col = line, col
            j = i
            while j < n and _is_word_char(src[j]):
                j += 1
            word = src[i:j]
            low = word.lower()
            if j < n and src[j].isdigit():
                raise syntax(
                    "I found the digit %s right after the word %s on line %s." % (src[j], word, line),
                    "Names use letters only, and digits only appear inside numbers. Try %s 2 instead of %s2." % (word, word))
            if low == "note":
                skip_note(start_line)
                continue
            if low == "text":
                # "text version of" is an operator phrase, not a literal
                if not (_match_word(src, j + 1, "version") and _match_word(src, j + 9, "of")):
                    if j >= n or src[j].isspace():
                        content, tok = read_text_literal(start_line, start_col)
                        tokens.append(tok)
                        continue
                # else fall through: a normal word like "texts"
            tokens.append(Token(WORD, low, word, start_line, start_col))
            advance(j - i)
            continue
        # forbidden symbol
        name, fix = SYMBOL_SUGGESTIONS.get(ch, (None, None))
        if name is None:
            name = "symbol %s" % ch
            fix = GENERIC_SUGGESTION
        raise PlainSyntaxError(
            "I found a %s on line %s." % (name, line),
            fix,
            line=line,
            source=source)

    tokens.append(Token(EOF, None, "", line, col))
    return tokens
