"""Tests for the Language Server Protocol server."""

import json
import subprocess
import sys
import threading

from plain.lsp import LanguageServer, diagnostics_for


class TestDiagnostics:
    def test_good_program_has_no_diagnostics(self):
        assert diagnostics_for("Say text hi end text.") == []

    def test_syntax_error_becomes_diagnostic(self):
        diagnostics = diagnostics_for("Say 1 plus.\n")
        assert len(diagnostics) == 1
        assert diagnostics[0]["severity"] == 1
        assert diagnostics[0]["source"] == "plain"
        assert diagnostics[0]["range"]["start"]["line"] == 0

    def test_diagnostic_points_at_line(self):
        diagnostics = diagnostics_for("Set x to 1.\nSay y plus.\n")
        assert diagnostics[0]["range"]["start"]["line"] == 1

    def test_diagnostic_includes_the_fix(self):
        diagnostics = diagnostics_for("Set total to 3 + 4.")
        assert "plus" in diagnostics[0]["message"]

    def test_incomplete_program_becomes_diagnostic(self):
        diagnostics = diagnostics_for("If yes, then")
        assert len(diagnostics) == 1


class io_stub:
    def __init__(self):
        self.buffer = b""
        self.waiting = threading.Semaphore(0)
        self.lock = threading.Lock()

    def read(self, n=-1):
        if n == -1:
            self.waiting.acquire(timeout=5)
            with self.lock:
                data = self.buffer
                self.buffer = b""
            return data
        while True:
            with self.lock:
                if len(self.buffer) >= n:
                    data = self.buffer[:n]
                    self.buffer = self.buffer[n:]
                    return data
            self.waiting.acquire(timeout=5)

    def write(self, data):
        with self.lock:
            self.buffer += data
        for _ in range(len(data)):
            self.waiting.release()
        return len(data)


class TestServerOverPipe:
    def test_initialize_and_diagnostics(self):
        client_to_server = io_stub()
        server_to_client = io_stub()
        server = LanguageServer(read=client_to_server.read, write=server_to_client.write)
        thread = threading.Thread(target=server.serve, daemon=True)
        thread.start()

        body = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"capabilities": {}},
        }).encode("utf-8")
        client_to_server.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))

        body = json.dumps({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": "file:///x.pln", "text": "Say 1 plus."}},
        }).encode("utf-8")
        client_to_server.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))

        raw = server_to_client.read(-1)
        text = raw.decode("utf-8")
        assert "initialize" in text or "publishDiagnostics" in text
        assert "plain" in text

    def test_cli_subcommand_exists(self):
        result = subprocess.run(
            [sys.executable, "-m", "plain", "--help"],
            capture_output=True, text=True)
        assert "lsp" in result.stdout


class TestServerEndToEnd:
    def test_full_session_over_real_process(self):
        def frame(payload):
            body = json.dumps(payload).encode("utf-8")
            return b"Content-Length: %d\r\n\r\n%s" % (len(body), body)

        payload = b"".join([
            frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            frame({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": "file:///bad.pln", "languageId": "plain",
                                 "version": 1, "text": "Set total to 3 + 4.\n"}}}),
            frame({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {
                "textDocument": {"uri": "file:///bad.pln", "version": 2},
                "contentChanges": [{"text": "Set total to 3 plus 4.\nSay total.\n"}]}}),
        ])
        result = subprocess.run(
            [sys.executable, "-m", "plain", "lsp"],
            input=payload, capture_output=True, timeout=30)
        text = result.stdout.decode("utf-8")
        assert "plain-language-server" in text
        assert "I found a plus sign on line 1" in text
        assert "Use the word plus instead" in text
        after_fix = text.rsplit("publishDiagnostics", 1)[-1]
        assert '"diagnostics": []' in after_fix
