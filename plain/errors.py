"""Error types for the Plain language.

Every Plain error is friendly: it names the line, quotes the offending
line of source, explains the problem in a sentence, and suggests a fix.
"""


def quote_line(source, line):
    """Return the text of the given 1-based line, or None if unknown."""
    if source is None or line is None:
        return None
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return None


class PlainError(Exception):
    """Base class for all errors Plain reports to the user."""

    kind = "problem"

    def __init__(self, problem, fix=None, line=None, source=None):
        super().__init__(problem)
        self.problem = problem
        self.fix = fix
        self.line = line
        self.source = source

    def render(self):
        parts = []
        if self.line is not None:
            parts.append("I found a %s on line %s of the Plain program:" % (self.kind, self.line))
        else:
            parts.append("I found a %s in the Plain program:" % self.kind)
        text = quote_line(self.source, self.line)
        if text is not None and text.strip():
            parts.append("    " + text.strip())
        parts.append(self.problem)
        if self.fix:
            parts.append(self.fix)
        return "\n".join(parts)

    def __str__(self):
        return self.render()


class PlainSyntaxError(PlainError):
    """The source code does not follow the grammar of Plain."""

    kind = "syntax problem"


class PlainRuntimeError(PlainError):
    """The program was understood, but something went wrong while running it."""

    kind = "runtime problem"


class PlainIncomplete(Exception):
    """The source ended in the middle of a statement.

    The REPL uses this to decide that it should keep reading lines.
    """

    def __init__(self, problem):
        super().__init__(problem)
        self.problem = problem

    def __str__(self):
        return self.problem