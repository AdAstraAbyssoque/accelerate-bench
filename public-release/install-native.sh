#!/usr/bin/env bash
set -euo pipefail
# Creates a fresh environment. It does not install Docker or start a benchmark.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${1:-.venv-native}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if [[ -e "$VENV_PATH" ]]; then
  echo 'Refusing to replace an existing environment.' >&2
  exit 1
fi
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 12), "Python >=3.12 required"'
"$PYTHON_BIN" -m venv "$VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --index-url https://pypi.org/simple -r "$SCRIPT_DIR/requirements-native.txt"
"$VENV_PATH/bin/python" -m pip check
"$VENV_PATH/bin/harbor" --version
