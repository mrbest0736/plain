"""A minimal Language Server Protocol server for Plain.

Speaks JSON-RPC 2.0 over stdio so editors such as VS Code and Cursor can show
friendly diagnostics for .pln files.  It implements only what the Plain editor
extension needs: initialize, textDocument/didOpen, textDocument/didChange,
textDocument/didClose, shutdown and exit.

Start it with:  python -m plain lsp
"""

import json
import sys

from plain import VERSION
from plain.errors import PlainError, PlainIncomplete
from plain.lexer import lex
from plain.parser import Parser

SERVER_NAME = "plain-language-server"
SERVER_VERSION = VERSION


def _diagnostic(problem, fix, line, source):
    """Build one LSP diagnostic from a Plain error."""
    line_index = max(0, (line or 1) - 1)
    lines = source.splitlines()
    end_character = len(lines[line_index]) if line_index < len(lines) else 0
    message = problem
    if fix:
        message = problem + " " + fix
    return {
        "range": {
            "start": {"line": line_index, "character": 0},
            "end": {"line": line_index, "character": end_character},
        },
        "severity": 1,
        "source": "plain",
        "message": message,
    }


def diagnostics_for(source):
    """Lex and parse the source; return a list of LSP diagnostics."""
    try:
        tokens = lex(source)
        Parser(tokens, source).parse_program()
    except PlainIncomplete as exc:
        return [{
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 0},
            },
            "severity": 1,
            "source": "plain",
            "message": exc.problem,
        }]
    except PlainError as exc:
        return [_diagnostic(exc.problem, exc.fix, exc.line, exc.source)]
    return []


class LanguageServer:
    def __init__(self, read=None, write=None, flush=None):
        self.read = read if read is not None else sys.stdin.buffer.read
        self.write = write if write is not None else sys.stdout.buffer.write
        self.flush = flush if flush is not None else sys.stdout.buffer.flush
        self.documents = {}
        self.shutdown_requested = False

    def serve(self):
        while True:
            message = self._read_message()
            if message is None:
                break
            self._handle(message)
            if self.shutdown_requested and message.get("method") == "exit":
                break

    def _read_message(self):
        headers = {}
        while True:
            line = self._read_header_line()
            if line is None:
                return None
            if line == "":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = self.read(length)
        if len(body) < length:
            return None
        return json.loads(body.decode("utf-8"))

    def _read_header_line(self):
        chars = []
        while True:
            char = self.read(1)
            if not char:
                return None
            if char == b"\n":
                if chars and chars[-1] == b"\r":
                    chars.pop()
                return b"".join(chars).decode("ascii")
            chars.append(char)

    def _send(self, method_or_id, result=None, is_response=False, method=None, params=None):
        if is_response:
            payload = {"jsonrpc": "2.0", "id": method_or_id, "result": result}
        else:
            payload = {"jsonrpc": "2.0", "method": method, "params": params}
        body = json.dumps(payload).encode("utf-8")
        self.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))
        self.flush()

    def _handle(self, message):
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            self._send(request_id, {
                "capabilities": {
                    "textDocumentSync": {"openClose": True, "change": 1},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }, is_response=True)
        elif method == "initialized":
            pass
        elif method == "textDocument/didOpen":
            document = params["textDocument"]
            self.documents[document["uri"]] = document.get("text", "")
            self._publish(document["uri"])
        elif method == "textDocument/didChange":
            document = params["textDocument"]
            changes = params.get("contentChanges") or []
            if changes:
                self.documents[document["uri"]] = changes[-1].get("text", "")
            self._publish(document["uri"])
        elif method == "textDocument/didClose":
            self.documents.pop(params["textDocument"]["uri"], None)
        elif method == "shutdown":
            self.shutdown_requested = True
            self._send(request_id, None, is_response=True)
        elif method == "exit":
            self.shutdown_requested = True

    def _publish(self, uri):
        source = self.documents.get(uri, "")
        self._send(None, method="textDocument/publishDiagnostics", params={
            "uri": uri,
            "diagnostics": diagnostics_for(source),
        })


def main():
    LanguageServer().serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
