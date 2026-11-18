#!/usr/bin/env bash
set -euo pipefail
uv version --package jupyter-book-marimo --no-sync "$1"
python3 scripts/release-metadata.py --sync
