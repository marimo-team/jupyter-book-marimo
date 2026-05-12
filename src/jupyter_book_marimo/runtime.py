"""Choose where marimo extraction runs for a transformed page.

Most pages run in-process; pages with ``options.marimo.pyproject`` run through
``uv`` so their dependencies stay local to the page authoring contract.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager, redirect_stdout
import importlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
import tempfile
from typing import Any

from .authoring import pyproject_to_script_metadata

UV_RUN_TIMEOUT_SECONDS = 300


async def extract(payload: dict[str, Any]) -> dict[str, Any]:
    """Import lazily so plugin discovery does not load execution code."""
    from .extract import extract as real_extract

    return await real_extract(payload)


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sandbox_env() -> dict[str, str]:
    """Prepend local src to PYTHONPATH so uv runs this checkout."""
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    paths = [str(source_root())]
    if pythonpath:
        paths.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


@contextmanager
def uv_run_args(pyproject: str) -> Generator[list[str], None, None]:
    # marimo moved sandbox helpers across private modules; support both import
    # paths so this plugin can share marimo's dependency parser across versions.
    try:
        sandbox_module = importlib.import_module("marimo._internal.sandbox")
    except ImportError:
        sandbox_module = importlib.import_module("marimo._cli.sandbox")
        metadata_module = importlib.import_module(
            "marimo._utils.inline_script_metadata"
        )
        pyproject_reader = metadata_module.PyProjectReader
    else:
        pyproject_reader = sandbox_module.PyProjectReader

    script_metadata = pyproject_to_script_metadata(pyproject)
    pyproject_config = pyproject_reader.from_script(script_metadata)
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-") as temp_dir:
        # construct_uv_flags writes requirements/constraints beside this file;
        # keep that scratch state scoped to one page extraction.
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=temp_dir, suffix=".txt"
        ) as temp_file:
            flags = sandbox_module.construct_uv_flags(
                pyproject_config, temp_file, [], []
            )
            temp_file.flush()
        yield ["run", *flags]  # type: ignore[misc]


def run_extractor(payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch extraction in-process unless page metadata requests uv."""
    metadata = payload.get("metadata")
    pyproject = metadata.get("pyproject") if isinstance(metadata, dict) else None
    if isinstance(pyproject, str) and pyproject.strip():
        with uv_run_args(pyproject) as args:
            args.extend(["python", "-m", "jupyter_book_marimo.extract"])
            command = ["uv", *args]
            try:
                result = subprocess.run(
                    command,
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=UV_RUN_TIMEOUT_SECONDS,
                    env=sandbox_env(),
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

    # MyST reads extractor JSON from stdout; user cell stdout must stay off it.
    with redirect_stdout(sys.stderr):
        return asyncio.run(extract(payload))


def main() -> None:
    payload = json.loads(sys.stdin.read())
    # Subprocess callers expect stdout to be JSON only; diagnostics belong on stderr.
    sys.stdout.write(json.dumps(run_extractor(payload)))
