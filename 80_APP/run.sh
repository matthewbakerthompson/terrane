#!/usr/bin/env bash
# Starts the local architecture model app.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$here/app/server.py" "$@"
