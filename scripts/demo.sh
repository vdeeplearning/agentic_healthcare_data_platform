#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
venv="$repo/.venv"
if [ ! -x "$venv/bin/python" ]; then python3 -m venv "$venv"; fi
"$venv/bin/python" -m pip install -e "$repo"
cd "$repo"
exec "$venv/bin/python" -m scripts.demo "$@"
