#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(dirname -- "$script_dir")
source_root="$project_root/src"

if command -v python3 >/dev/null 2>&1; then
  python_command=python3
elif command -v python >/dev/null 2>&1; then
  python_command=python
else
  echo "Python 3.11 or newer was not found." >&2
  exit 1
fi

"$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11 or newer is required." >&2
  exit 1
}

PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" exec "$python_command" -m luna_agent "$@"
