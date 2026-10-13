#!/usr/bin/env bash
# Run the vault search scripts in their own venv. Normal runs never install anything;
# `--setup` (an explicit, one-time step) creates the venv from vault-search-requirements.txt.
set -euo pipefail
SETUP=false
if [ "${1:-}" = "--setup" ]; then
  SETUP=true
  shift
fi
export PYTHONDONTWRITEBYTECODE=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ="$SCRIPT_DIR/vault-search-requirements.txt"
VENV="${VAULT_SEARCH_VENV:-$HOME/.venvs/vault-search}"

if [ ! -r "$REQ" ]; then
  printf 'Requirements file is unavailable: %s\n' "$REQ" >&2
  exit 2
fi
# Ready = venv exists, was built from the current requirements, and imports cleanly.
if [ ! -x "$VENV/bin/python" ] || ! cmp -s "$REQ" "$VENV/.requirements.txt" || \
   ! "$VENV/bin/python" -B -c 'import numpy, yaml' >/dev/null 2>&1; then
  if [ "$SETUP" != true ]; then
    printf 'The vault search environment is missing or out of date: %s\n' "$VENV" >&2
    printf 'Run once: bash %q --setup\n' "$SCRIPT_DIR/vault-python.sh" >&2
    exit 2
  fi
  printf 'Preparing the vault search environment in %s\n' "$VENV" >&2
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv --clear "$VENV"
  "$VENV/bin/python" -B -m pip install --disable-pip-version-check -r "$REQ" >&2
  "$VENV/bin/python" -B -c 'import numpy, yaml'
  cp "$REQ" "$VENV/.requirements.txt"
fi
if [ "$SETUP" = true ] && [ "$#" -eq 0 ]; then
  printf 'The vault search environment is ready: %s\n' "$VENV" >&2
  exit 0
fi
exec "$VENV/bin/python" -B "$@"
