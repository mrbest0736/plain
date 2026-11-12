"""Plain -- a programming language written in English words."""

VERSION = "1.1"

from plain.errors import PlainError, PlainSyntaxError, PlainRuntimeError, PlainIncomplete
from plain.lexer import lex, Token
from plain.parser import Parser
from plain.ast_nodes import Program
from plain.interpreter import Interpreter

__all__ = [
    "VERSION",
    "PlainError",
    "PlainSyntaxError",
    "PlainRuntimeError",
    "PlainIncomplete",
    "lex",
    "Token",
    "Parser",
    "Program",
    "Interpreter",
]
