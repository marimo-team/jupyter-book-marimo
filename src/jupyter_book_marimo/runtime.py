"""Run marimo extraction either in-process or in a page-local uv sandbox."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .extract import extract
from .sandbox import uv_run_args


def extractor_path() -> Path:
    return Path(__file__).with_name("extract.py")


def run_extractor(payload: dict[str, Any]) -> dict[str, Any]:
    pyproject = payload.get("metadata", {}).get("pyproject")
    if isinstance(pyproject, str) and pyproject.strip():
        args = uv_run_args(pyproject)
        args.extend(["python", str(extractor_path())])
        result = subprocess.run(
            ["uv", *args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"marimo extraction failed\n{result.stderr}\n{result.stdout}".strip()
            )
        return json.loads(result.stdout)

    return asyncio.run(extract(payload))


def main() -> None:
    payload = json.loads(sys.stdin.read())
    sys.stdout.write(json.dumps(run_extractor(payload)))
