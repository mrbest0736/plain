/* Plain language extension for VS Code and Cursor.
 *
 * No npm dependencies: it speaks LSP over stdio directly to
 * `python -m plain lsp`, forwards diagnostics, and adds run/check commands.
 */

const vscode = require("vscode");
const { spawn } = require("child_process");

let server = null;
let serverBuffer = Buffer.alloc(0);
let outputChannel = null;
let restarting = false;
let diagnosticCollection = null;
const pendingResponses = new Map();
let nextRequestId = 1;

function pythonPath() {
    return vscode.workspace.getConfiguration("plain").get("pythonPath", "python3");
}

function diagnosticsEnabled() {
    return vscode.workspace.getConfiguration("plain").get("diagnostics", true);
}

function startServer(context) {
    if (server) {
        try { server.kill(); } catch (err) { /* already gone */ }
        server = null;
    }
    log("Starting Plain language server: " + pythonPath() + " -m plain lsp");
    const child = spawn(pythonPath(), ["-m", "plain", "lsp"], {
        env: process.env,
    });

    child.stdout.on("data", (chunk) => {
        serverBuffer = Buffer.concat([serverBuffer, chunk]);
        drainServerMessages();
    });
    child.stderr.on("data", (chunk) => {
        log("server: " + chunk.toString().trim());
    });
    child.on("error", (err) => {
        log("could not start the language server: " + err.message);
        vscode.window.showInformationMessage(
            "Plain: the language server could not start. Install the plain package with: pip install plain-language"
        );
    });
    child.on("exit", (code) => {
        log("language server exited with code " + code);
        server = null;
        if (!restarting && code && code !== 0) {
            log("unexpected exit; use the command Plain: Restart Language Server to try again");
        }
    });

    server = child;
    context.subscriptions.push(child);

    for (const document of vscode.workspace.textDocuments) {
        if (document.languageId === "plain") {
            sendOpen(document);
        }
    }
}

function drainServerMessages() {
    while (true) {
        const headerEnd = serverBuffer.indexOf("\r\n\r\n");
        if (headerEnd < 0) {
            return;
        }
        const header = serverBuffer.slice(0, headerEnd).toString("utf8");
        const match = /content-length:\s*(\d+)/i.exec(header);
        if (!match) {
            return;
        }
        const length = parseInt(match[1], 10);
        const bodyStart = headerEnd + 4;
        if (serverBuffer.length < bodyStart + length) {
            return;
        }
        const body = serverBuffer.slice(bodyStart, bodyStart + length).toString("utf8");
        serverBuffer = serverBuffer.slice(bodyStart + length);
        handleServerMessage(JSON.parse(body));
    }
}

function handleServerMessage(message) {
    if (message.method === "textDocument/publishDiagnostics") {
        const uri = vscode.Uri.parse(message.params.uri);
        const diagnostics = (message.params.diagnostics || []).map((item) => {
            const start = new vscode.Position(item.range.start.line, item.range.start.character);
            const end = new vscode.Position(item.range.end.line, item.range.end.character);
            return new vscode.Diagnostic(
                new vscode.Range(start, end),
                item.message,
                vscode.DiagnosticSeverity.Error
            );
        });
        diagnosticCollection.set(uri, diagnostics);
    } else if (message.id !== undefined && pendingResponses.has(message.id)) {
        const resolve = pendingResponses.get(message.id);
        pendingResponses.delete(message.id);
        resolve(message);
    }
}

function sendMessage(payload) {
    if (!server) {
        return;
    }
    const body = Buffer.from(JSON.stringify(payload), "utf8");
    const header = Buffer.from("Content-Length: " + body.length + "\r\n\r\n", "ascii");
    server.stdin.write(Buffer.concat([header, body]));
}

function sendRequest(method, params) {
    return new Promise((resolve) => {
        const id = nextRequestId;
        nextRequestId += 1;
        pendingResponses.set(id, resolve);
        sendMessage({ jsonrpc: "2.0", id: id, method: method, params: params });
    });
}

function sendNotification(method, params) {
    sendMessage({ jsonrpc: "2.0", method: method, params: params });
}

function sendOpen(document) {
    if (!server || !diagnosticsEnabled()) {
        return;
    }
    sendNotification("textDocument/didOpen", {
        textDocument: {
            uri: String(document.uri),
            languageId: "plain",
            version: document.version,
            text: document.getText(),
        },
    });
}

function sendChange(event) {
    if (!server || !diagnosticsEnabled()) {
        return;
    }
    sendNotification("textDocument/didChange", {
        textDocument: {
            uri: String(event.document.uri),
            version: event.document.version,
        },
        contentChanges: [{ text: event.document.getText() }],
    });
}

function sendClose(document) {
    if (!server) {
        return;
    }
    sendNotification("textDocument/didClose", {
        textDocument: { uri: String(document.uri) },
    });
}

function runFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "plain") {
        vscode.window.showInformationMessage("Open a .pln file to run it.");
        return;
    }
    const terminal = vscode.window.createTerminal({ name: "Plain" });
    terminal.show();
    terminal.sendText('"' + pythonPath() + '" -m plain run "' + editor.document.fileName + '"');
}

function checkFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "plain") {
        vscode.window.showInformationMessage("Open a .pln file to check it.");
        return;
    }
    const terminal = vscode.window.createTerminal({ name: "Plain" });
    terminal.show();
    terminal.sendText('"' + pythonPath() + '" -m plain check "' + editor.document.fileName + '"');
}

function log(text) {
    if (!outputChannel) {
        outputChannel = vscode.window.createOutputChannel("Plain Language");
    }
    outputChannel.appendLine(text);
}

function activate(context) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection("plain");
    context.subscriptions.push(diagnosticCollection);
    context.subscriptions.push(
        vscode.commands.registerCommand("plain.runFile", runFile),
        vscode.commands.registerCommand("plain.checkFile", checkFile),
        vscode.commands.registerCommand("plain.restartServer", async () => {
            restarting = true;
            startServer(context);
            restarting = false;
            vscode.window.showInformationMessage("Plain language server restarted.");
        }),
        vscode.workspace.onDidOpenTextDocument((document) => {
            if (document.languageId === "plain") {
                sendOpen(document);
            }
        }),
        vscode.workspace.onDidChangeTextDocument((event) => {
            if (event.document.languageId === "plain") {
                sendChange(event);
            }
        }),
        vscode.workspace.onDidCloseTextDocument((document) => {
            if (document.languageId === "plain") {
                sendClose(document);
            }
        })
    );
    startServer(context);
}

function deactivate() {
    if (server) {
        try {
            sendRequest("shutdown", null);
            sendNotification("exit", null);
            server.kill();
        } catch (err) { /* already gone */ }
        server = null;
    }
}

module.exports = { activate, deactivate };
