"""The Plain command line interface.

    plain run file.pln     run a program
    plain check file.pln   check the syntax without running it
    plain color file.pln   print the program colour coded for the terminal
    plain repl             start an interactive session
    plain version          show the version
"""

import argparse
import sys

from plain import VERSION
from plain.errors import PlainError, PlainIncomplete
from plain.lexer import lex
from plain.parser import Parser
from plain.interpreter import Interpreter
from plain.vm import Runtime
from plain.security import Limits

REPL_HELP = """Plain is a programming language written in English words.

Try things like:
    Set score to 10.
    Change score by 5.
    Say text Hello, world. end text
    If score is greater than 5, then Say text big end text. end if.
    Make a list called scores holding 1, 2, 3.
    Say item 2 of scores.
    To double with n, do give back n times 2. end function.
    Say the result of double with 21.

Tips:
    Every statement ends with a period.
    Words are case-insensitive and names can be several words.
    Type an expression by itself (like score plus 1) to see its value.
    Type help for this message, or bye to leave."""


def load_program(path):
    """Read, lex and parse a .pln file. Raises PlainError on problems."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except FileNotFoundError:
        raise PlainError(
            "I could not find a file called %s." % path,
            "Check the file name. Plain programs usually end in .pln")
    except OSError as exc:
        raise PlainError(
            "I could not read the file %s because %s." % (path, exc.strerror or exc),
            "Check that the file exists and can be read.")
    tokens = lex(source)
    program = Parser(tokens, source).parse_program()
    return program, source


def limits_from_args(args):
    """Build a Limits from the --max-* and --no-limits flags."""
    if getattr(args, "no_limits", False):
        return Limits.unlimited()
    return Limits(
        max_loop_rounds=getattr(args, "max_loop_rounds", None),
        max_call_depth=getattr(args, "max_call_depth", None),
        max_output_chars=getattr(args, "max_output_chars", None),
        max_wait_seconds=getattr(args, "max_wait_seconds", None),
        max_read_bytes=getattr(args, "max_read_bytes", None),
    )


def cmd_run(args):
    program, source = load_program(args.file)
    limits = limits_from_args(args)
    if getattr(args, "tree", False):
        engine = Interpreter(source=source, filename=args.file, limits=limits)
    else:
        engine = Runtime(source=source, filename=args.file, limits=limits)
    engine.run(program)
    return 0


def cmd_color(args):
    from plain.highlight import highlight_source
    program, source = load_program(args.file)
    sys.stdout.write(highlight_source(source))
    if not source.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_check(args):
    program, _source = load_program(args.file)
    count = len(program.statements)
    if count == 1:
        print("No problems found. %s looks good, with 1 statement." % args.file)
    else:
        print("No problems found. %s looks good, with %s statements." % (args.file, count))
    return 0


def _is_statement_complete(source):
    """Return (complete, program_or_None, error_or_None)."""
    try:
        tokens = lex(source)
        program = Parser(tokens, source).parse_program()
    except PlainIncomplete as exc:
        return False, None, exc
    except PlainError as exc:
        return True, None, exc
    return True, program, None


def cmd_repl(args):
    sys.stdout.write("Plain version %s. Type help for help, or bye to leave.\n" % VERSION.replace(".", " point "))
    buffer = []
    scope_interp = Interpreter(source="")
    while True:
        prompt = "plain> " if not buffer else "   ... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\nBye.\n")
            return 0
        stripped = line.strip().lower()
        if not buffer and stripped in ("bye", "bye.", "exit", "exit.", "quit", "quit."):
            sys.stdout.write("Bye.\n")
            return 0
        if not buffer and stripped in ("help", "help."):
            sys.stdout.write(REPL_HELP + "\n")
            continue
        buffer.append(line)
        source = "\n".join(buffer)
        complete, program, error = _is_statement_complete(source)
        if not complete:
            continue
        buffer = []
        if error is None:
            try:
                scope_interp.run(program)
            except PlainError as exc:
                sys.stdout.write(str(exc) + "\n")
            continue
        # Not a valid statement. Maybe it is a bare expression.
        value = _try_expression(scope_interp, source)
        if value is not _NO_VALUE:
            from plain.builtins import display_value
            sys.stdout.write(display_value(value) + "\n")
        else:
            sys.stdout.write(str(error) + "\n")
    return 0


_NO_VALUE = object()


def _try_expression(interp, source):
    try:
        tokens = lex(source)
        if len(tokens) > 2 and tokens[-2].type == "PERIOD":
            tokens = tokens[:-2] + [tokens[-1]]
        parser = Parser(tokens, source)
        node = parser.parse_expression_only()
    except PlainError:
        return _NO_VALUE
    try:
        return interp.eval(node, interp.globals)
    except PlainError as exc:
        sys.stdout.write(str(exc) + "\n")
        return _NO_VALUE


def cmd_version(args):
    print("Plain version %s" % VERSION.replace(".", " point "))
    return 0


def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="plain",
        description="Plain: a programming language written in English words.")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="run a .pln program")
    run_p.add_argument("file", help="the .pln file to run")
    run_p.add_argument("--tree", action="store_true",
                       help="use the reference tree-walking interpreter instead of the compiled runner")
    for flag, dest, default, help_text in (
        ("--max-loop-rounds", "max_loop_rounds", Limits.max_loop_rounds,
         "total loop rounds allowed before the program is stopped"),
        ("--max-call-depth", "max_call_depth", Limits.max_call_depth,
         "how deep function calls may nest"),
        ("--max-output-chars", "max_output_chars", Limits.max_output_chars,
         "characters the program may print"),
        ("--max-wait-seconds", "max_wait_seconds", Limits.max_wait_seconds,
         "longest single wait allowed"),
        ("--max-read-bytes", "max_read_bytes", Limits.max_read_bytes,
         "largest file the program may read"),
    ):
        run_p.add_argument(flag, dest=dest, type=int, default=default, help=help_text)
    run_p.add_argument("--no-limits", action="store_true",
                       help="turn off all safety limits (not recommended)")
    check_p = sub.add_parser("check", help="check the syntax of a .pln program")
    check_p.add_argument("file", help="the .pln file to check")
    color_p = sub.add_parser("color", help="print a .pln program colour coded")
    color_p.add_argument("file", help="the .pln file to colour code")
    sub.add_parser("repl", help="start an interactive Plain session")
    sub.add_parser("lsp", help="run the language server for editors (VS Code, Cursor)")
    sub.add_parser("version", help="show the version of Plain")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        try:
            return cmd_run(args)
        except PlainError as exc:
            sys.stdout.write(str(exc) + "\n")
            return 1
    if args.command == "check":
        try:
            return cmd_check(args)
        except PlainError as exc:
            sys.stdout.write(str(exc) + "\n")
            return 1
    if args.command == "color":
        try:
            return cmd_color(args)
        except PlainError as exc:
            sys.stdout.write(str(exc) + "\n")
            return 1
    if args.command == "repl":
        return cmd_repl(args)
    if args.command == "lsp":
        from plain.lsp import main as lsp_main
        return lsp_main()
    if args.command == "version":
        return cmd_version(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
