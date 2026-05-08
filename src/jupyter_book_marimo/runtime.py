"""Run marimo extraction either in-process or in a page-local uv sandbox."""

from __future__ import annotations

import asyncio
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from .extract import extract
from .sandbox import uv_run_args

UV_RUN_TIMEOUT_SECONDS = 300


def extractor_path() -> Path:
    return Path(__file__).with_name("extract.py")


def run_extractor(payload: dict[str, Any]) -> dict[str, Any]:
    pyproject = payload.get("metadata", {}).get("pyproject")
    if isinstance(pyproject, str) and pyproject.strip():
        with uv_run_args(pyproject) as args:
            args.extend(["python", str(extractor_path())])
            command = ["uv", *args]
            try:
                result = subprocess.run(
                    command,
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=UV_RUN_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    "marimo extraction timed out after "
                    f"{UV_RUN_TIMEOUT_SECONDS}s while running {shlex.join(command)}"
                ) from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"marimo extraction failed\n{result.stderr}\n{result.stdout}".strip()
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "marimo extraction returned invalid JSON while running "
                f"{shlex.join(command)}\n{result.stderr}\n{result.stdout}".strip()
            ) from exc

    return asyncio.run(extract(payload))


def main() -> None:
    payload = json.loads(sys.stdin.read())
    sys.stdout.write(json.dumps(run_extractor(payload)))
