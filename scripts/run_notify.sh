#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

chmod 600 config.yaml 2>/dev/null || true
chmod 600 telegram.yaml 2>/dev/null || true

"$PY" orchestrate_notify.py
