# Plain Language — editor extension

Syntax highlighting, snippets, live friendly diagnostics and one-command
running for the **Plain** programming language (`.pln` files). Works in
**VS Code**, **Cursor**, **VSCodium** and any editor that supports VS Code
extensions.

![Plain logo](icon.png)

## What you get

- **Syntax highlighting** for every Plain construct: keywords, operator words
  (`plus`, `times`, `is greater than`, ...), `text ... end text` literals,
  `Note ... end note` comments, numbers, `yes`/`no`/`nothing`.
- **16 snippets** — type `if`, `repeat`, `function`, `try`, `makelist`, ... and Tab.
- **Live diagnostics**: friendly Plain error messages as red squiggles while
  you type, powered by the Plain language server (`python -m plain lsp`).
- **Commands**: `Plain: Run File` and `Plain: Check File` from the command
  palette, plus `Plain: Restart Language Server`.
- **File icon** for `.pln` files and block-comment toggling with
  `Note ... end note`.

## Install

### 1. Install the Plain language itself

The extension needs Python 3.8+ with the `plain` package:

```bash
pip install plain-language
```

(or from this project folder: `pip install .`)

### 2. Install the extension

**From the packaged file (recommended):**

1. Get `plain-language-1.0.0.vsix` from the `dist/` folder of this project.
2. In VS Code or Cursor: Extensions view (`Ctrl+Shift+X`) → `...` menu →
   **Install from VSIX...** → pick the file.
   Or from a terminal: `code --install-extension plain-language-1.0.0.vsix`
   (Cursor: `cursor --install-extension plain-language-1.0.0.vsix`).

**From the folder (development):** copy or symlink `editors/plain-vscode`
into `~/.vscode/extensions/plain-language` and reload the window.

### 3. Settings

| Setting | Default | What it does |
| --- | --- | --- |
| `plain.pythonPath` | `python3` | Python used for the language server and running files |
| `plain.diagnostics` | `true` | Live syntax squiggles while typing |

If the server cannot start, the extension still highlights and runs files —
check the **Plain Language** output channel for details.

## Building the .vsix yourself

The package is a plain zip with a manifest, so no Node toolchain is needed:

```bash
python3 tools/package_vsix.py
```

writes `dist/plain-language-1.0.0.vsix`. With `npm`/`vsce` installed you can
also run `vsce package` inside `editors/plain-vscode` for a marketplace-ready
build.

## Files

| File | Purpose |
| --- | --- |
| `package.json` | Extension manifest: language, grammar, snippets, commands, settings |
| `extension.js` | LSP client (no dependencies) + run/check commands |
| `syntaxes/plain.tmLanguage.json` | TextMate grammar for highlighting |
| `snippets/plain.json` | Snippets for every statement kind |
| `language-configuration.json` | Comments, word pattern, folding markers |
| `icon.png`, `assets/file-icon.svg` | The Plain logo |
