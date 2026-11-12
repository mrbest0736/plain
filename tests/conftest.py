import io

import pytest

from plain.errors import PlainError, PlainIncomplete, PlainRuntimeError, PlainSyntaxError
from plain.lexer import lex
from plain.parser import Parser
from plain.interpreter import Interpreter


def parse_src(src):
    return Parser(lex(src), src).parse_program()


def run_src(src, inputs=None, filename=None):
    out = []
    pending = list(inputs or [])

    def input_fn():
        if not pending:
            raise EOFError
        return pending.pop(0)

    interp = Interpreter(source=src, filename=filename, output=out.append, input_fn=input_fn)
    program = parse_src(src)
    interp.run(program)
    return "".join(out)


def run_error(src, inputs=None, filename=None):
    with pytest.raises(PlainError) as exc_info:
        run_src(src, inputs, filename=filename)
    return exc_info.value


def lex_error(src):
    with pytest.raises(PlainError) as exc_info:
        lex(src)
    return exc_info.value
