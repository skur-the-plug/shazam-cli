#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "shazam-cli currently supports Linux only." >&2
  exit 1
fi

for dependency in python3 pw-record pactl; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing system dependency: $dependency" >&2
    echo "See the README's Requirements section." >&2
    exit 1
  fi
done

if command -v uv >/dev/null 2>&1; then
  uv tool install --force "$REPO_DIR"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$REPO_DIR"
else
  INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/shazam-cli"
  BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
  python3 -m venv "$INSTALL_DIR"
  "$INSTALL_DIR/bin/python" -m pip install --upgrade "$REPO_DIR"
  mkdir -p "$BIN_DIR"
  ln -sfn "$INSTALL_DIR/bin/shazam" "$BIN_DIR/shazam"
fi

echo
echo "Installed. Try: shazam"
