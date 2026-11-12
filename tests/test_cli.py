import os

import pytest

from plain.cli import main, REPL_HELP

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def run_cli(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out


class TestVersion:
    def test_version(self, capsys):
        code, out = run_cli(capsys, ["version"])
        assert code == 0
        assert "Plain version 1 point 0" in out


class TestCheck:
    def test_check_good_file(self, capsys):
        code, out = run_cli(capsys, ["check", os.path.join(EXAMPLES, "hello.pln")])
        assert code == 0
        assert "No problems found" in out

    def test_check_bad_file(self, capsys, tmp_path):
        bad = tmp_path / "bad.pln"
        bad.write_text("Set x to 5 + 3.")
        code, out = run_cli(capsys, ["check", str(bad)])
        assert code == 1
        assert "plus sign" in out
        assert "Use the word plus instead." in out

    def test_check_missing_file(self, capsys, tmp_path):
        code, out = run_cli(capsys, ["check", str(tmp_path / "nope.pln")])
        assert code == 1
        assert "could not find a file" in out


class TestRun:
    def test_run_hello(self, capsys):
        code, out = run_cli(capsys, ["run", os.path.join(EXAMPLES, "hello.pln")])
        assert code == 0
        assert out == "Hello, world.\n"

    def test_run_runtime_error_exit_code(self, capsys, tmp_path):
        bad = tmp_path / "bad.pln"
        bad.write_text("Say mystery value.")
        code, out = run_cli(capsys, ["run", str(bad)])
        assert code == 1
        assert "mystery value" in out

    def test_run_missing_file(self, capsys, tmp_path):
        code, out = run_cli(capsys, ["run", str(tmp_path / "nope.pln")])
        assert code == 1
        assert "could not find a file" in out


class TestRepl:
    def repl(self, capsys, monkeypatch, lines):
        answers = list(lines)
        monkeypatch.setattr("builtins.input", lambda prompt="": answers.pop(0))
        code = main(["repl"])
        captured = capsys.readouterr()
        return code, captured.out

    def test_repl_banner_and_bye(self, capsys, monkeypatch):
        code, out = self.repl(capsys, monkeypatch, ["bye"])
        assert code == 0
        assert "Plain version 1 point 0" in out
        assert "Bye." in out

    def test_repl_help(self, capsys, monkeypatch):
        code, out = self.repl(capsys, monkeypatch, ["help", "bye"])
        assert REPL_HELP in out

    def test_repl_state_persists(self, capsys, monkeypatch):
        code, out = self.repl(capsys, monkeypatch, ["Set x to 21.", "x times 2.", "bye"])
        assert "42" in out

    def test_repl_bare_expression(self, capsys, monkeypatch):
        code, out = self.repl(capsys, monkeypatch, ["2 plus 3.", "bye"])
        assert "5" in out

    def test_repl_multiline(self, capsys, monkeypatch):
        lines = ["If yes, then", "Say text big end text.", "end if.", "bye"]
        code, out = self.repl(capsys, monkeypatch, lines)
        assert "big" in out

    def test_repl_error_keeps_going(self, capsys, monkeypatch):
        code, out = self.repl(capsys, monkeypatch, ["Say mystery value.", "Say text ok end text.", "bye"])
        assert "mystery value" in out
        assert "ok" in out
