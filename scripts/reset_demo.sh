#!/usr/bin/env sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python="$repo/.venv/bin/python"
if [ ! -x "$python" ]; then python=python3; fi
cd "$repo"
exec "$python" -m scripts.demo --reset
