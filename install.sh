#!/bin/sh
set -e
cd "$(dirname "$0")"
echo "Installing the Plain language..."
python3 -m pip install --user .
echo "Building the editor extension..."
python3 tools/package_vsix.py
VSIX=$(ls dist/*.vsix 2>/dev/null | head -n 1)
if [ -z "$VSIX" ]; then
  echo "No .vsix file was found in dist after building."
  exit 1
fi
INSTALLED=0
if command -v code >/dev/null 2>&1; then
  code --install-extension "$VSIX"
  INSTALLED=1
fi
if command -v cursor >/dev/null 2>&1; then
  cursor --install-extension "$VSIX"
  INSTALLED=1
fi
if [ "$INSTALLED" = "0" ]; then
  echo "VS Code and Cursor were not found on PATH."
  echo "To install by hand: open the Extensions view, click ... and choose"
  echo "Install from VSIX, then pick $VSIX"
fi
echo "Done. Try it: plain run examples/hello.pln"
