"""Run every example program in examples/ and prove it works."""

import os

import pytest

from conftest import run_src

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def example(name):
    with open(os.path.join(EXAMPLES, name), "r", encoding="utf-8") as handle:
        return handle.read()


class TestNoStdinExamples:
    def test_hello(self):
        assert run_src(example("hello.pln")) == "Hello, world.\n"

    def test_fizzbuzz(self):
        out = run_src(example("fizzbuzz.pln"))
        lines = out.splitlines()
        assert lines == [
            "1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz",
            "Buzz", "11", "Fizz", "13", "14", "FizzBuzz",
        ]

    def test_fibonacci(self):
        out = run_src(example("fibonacci.pln"))
        assert "fibonacci number 10 is 55" in out
        assert "fibonacci number 1 is 1" in out

    def test_primes(self):
        out = run_src(example("primes.pln"))
        primes = [line.split()[0] for line in out.splitlines()]
        assert primes == ["2", "3", "5", "7", "11", "13", "17", "19",
                          "23", "29", "31", "37", "41", "43", "47"]

    def test_lists(self):
        out = run_src(example("lists.pln"))
        assert "The scores are [5, 10, 15, 20]" in out
        assert "Sorted, they are [5, 15, 20, 99]" in out
        assert "Item 2 of item 1 of the grid is 2" in out
        assert "The list has a 99 in it." in out

    def test_functions(self):
        out = run_src(example("functions.pln"))
        assert "Three plus four is 7" in out
        assert "Hello there. Ada Welcome to Plain." in out
        assert "The counter is now 3" in out
        assert "Larger is 12 and smaller is 12" in out

    def test_errors_example(self):
        out = run_src(example("errors.pln"))
        assert "That did not work." in out
        assert "divide" in out
        assert "All done, and the program kept going." in out

    def test_import_demo(self, tmp_path):
        # copy the helper next to a temp main so the import resolves
        import shutil
        shutil.copy(os.path.join(EXAMPLES, "helpers.pln"), tmp_path / "helpers.pln")
        main = tmp_path / "import_demo.pln"
        shutil.copy(os.path.join(EXAMPLES, "import_demo.pln"), main)
        out = run_src(main.read_text(), filename=str(main))
        assert "helpers are loaded." in out
        assert "Triple of 7 is 21" in out


class TestStdinExamples:
    def test_factorial(self):
        out = run_src(example("factorial.pln"), inputs=["5"])
        assert out == "The factorial of 5 is 120\n"

    def test_factorial_bad_then_good(self):
        out = run_src(example("factorial.pln"), inputs=["oops", "6"])
        assert "That is not a number." in out
        assert out.endswith("The factorial of 6 is 720\n")

    def test_guessing_game(self):
        inputs = [str(n) for n in range(1, 21)]
        out = run_src(example("guessing.pln"), inputs=inputs)
        assert "I am thinking of a number from 1 to 20." in out
        assert "You got it in" in out
        assert "tries." in out

    def test_temperature_celsius(self):
        out = run_src(example("temperature.pln"), inputs=["c", "100"])
        assert "That is 212 degrees Fahrenheit." in out

    def test_temperature_fahrenheit(self):
        out = run_src(example("temperature.pln"), inputs=["f", "212"])
        assert "That is 100 degrees Celsius." in out

    def test_temperature_unknown_choice(self):
        out = run_src(example("temperature.pln"), inputs=["z"])
        assert "I only know the letters c and f." in out

    def test_wordcount(self):
        out = run_src(example("wordcount.pln"), inputs=["the quick brown fox"])
        assert "4 words and 19 letters" in out
        assert "The first word is the" in out
        assert "The last word is fox" in out

    def test_calculator(self):
        out = run_src(example("calculator.pln"), inputs=["7", "times", "6"])
        assert "The answer is 42" in out

    def test_calculator_division(self):
        out = run_src(example("calculator.pln"), inputs=["7", "divided", "2"])
        assert "The answer is 3.5" in out

    def test_calculator_unknown_operation(self):
        out = run_src(example("calculator.pln"), inputs=["7", "power", "6"])
        assert "I only know plus, minus, times and divided." in out

    def test_todo_manager(self):
        inputs = ["buy milk", "wash car", "show", "done", "1", "show", "quit"]
        out = run_src(example("todo.pln"), inputs=inputs)
        assert "Added." in out
        assert "1 -- buy milk" in out
        assert "2 -- wash car" in out
        assert "Nice, that is done." in out
        assert "1 -- wash car" in out
        assert out.endswith("Bye!\n")


class TestAllExamplesParse:
    @pytest.mark.parametrize("name", sorted(os.listdir(EXAMPLES)))
    def test_every_example_is_valid_plain(self, name):
        if not name.endswith(".pln"):
            pytest.skip("not a program")
        from plain.lexer import lex
        from plain.parser import Parser
        source = example(name)
        program = Parser(lex(source), source).parse_program()
        assert program.statements


class TestEnginesAgreeOnExamples:
    """Every example must produce identical output on both engines."""

    @pytest.mark.parametrize("name", sorted(os.listdir(EXAMPLES)))
    def test_compiled_runner_matches_reference(self, name, monkeypatch, tmp_path):
        import io
        import shutil

        from plain import builtins
        from plain.interpreter import Interpreter
        from plain.lexer import lex
        from plain.parser import Parser
        from plain.vm import Runtime

        workdir = tmp_path / name.replace(".pln", "")
        workdir.mkdir()
        for item in os.listdir(EXAMPLES):
            if item.endswith(".pln"):
                shutil.copy(os.path.join(EXAMPLES, item), workdir / item)

        def run_on(engine_class, inputs):
            out = io.StringIO()
            pending = list(inputs)

            def input_fn():
                if not pending:
                    raise EOFError
                return pending.pop(0)

            source = (workdir / name).read_text(encoding="utf-8")
            engine = engine_class(source=source, filename=str(workdir / name),
                                  output=out.write, input_fn=input_fn)
            program = Parser(lex(source), source).parse_program()
            engine.run(program)
            return out.getvalue()

        inputs = {
            "factorial.pln": ["5"],
            "temperature.pln": ["c", "100"],
            "wordcount.pln": ["the quick brown fox jumps over the lazy dog"],
            "calculator.pln": ["12", "plus", "30"],
            "guessing.pln": [str(n) for n in range(1, 21)],
            "todo.pln": ["add buy milk", "add walk dog", "show", "done", "2", "show", "quit"],
        }.get(name, [])

        first = None
        for engine_class in (Interpreter, Runtime):
            builtins._random.seed(1234)
            output = run_on(engine_class, inputs)
            if first is None:
                first = output
            else:
                assert output == first
