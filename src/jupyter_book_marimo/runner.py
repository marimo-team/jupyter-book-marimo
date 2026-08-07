"""Run page compilation in the environment selected by page configuration."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from .authoring import pyproject_to_script_metadata
from .protocol import CompiledMarimoPage, MarimoPageRequest

MARIMO_REQUIREMENT = "marimo>=0.23.15"
UV_RUN_TIMEOUT_SECONDS = int(
    os.environ.get("JUPYTER_BOOK_MARIMO_UV_TIMEOUT_SECONDS", "300")
)


def run_page_compiler(
    request: MarimoPageRequest,
    *,
    external_env: bool = False,
) -> CompiledMarimoPage:
    if external_env or not request.metadata.pyproject.strip():
        return run_compiler_process(
            [sys.executable, "-m", "jupyter_book_marimo.compiler"],
            request,
            env=os.environ.copy(),
        )

    return run_uv_compiler(request)


def run_uv_compiler(request: MarimoPageRequest) -> CompiledMarimoPage:
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-") as temp_dir:
        script = Path(temp_dir) / "compile_page.py"
        script.write_text(
            pyproject_to_script_metadata(request.metadata.pyproject)
            + "\nfrom jupyter_book_marimo.compiler import main\n\n"
            + 'if __name__ == "__main__":\n'
            + "    main()\n",
            encoding="utf-8",
        )
        command = [
            *uv_command(),
            "run",
            "--no-project",
            "--with",
            MARIMO_REQUIREMENT,
            str(script),
        ]
        with compiler_environment() as env:
            return run_compiler_process(command, request, env=env)


def run_compiler_process(
    command: list[str],
    request: MarimoPageRequest,
    *,
    env: dict[str, str] | None = None,
) -> CompiledMarimoPage:
    try:
        result = subprocess.run(
            command,
            input=json.dumps(request.to_json()),
            text=True,
            capture_output=True,
            check=False,
            timeout=UV_RUN_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "marimo compilation timed out after "
            f"{UV_RUN_TIMEOUT_SECONDS}s while running {shlex.join(command)}"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"marimo compilation failed\n{result.stderr}\n{result.stdout}".strip()
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "marimo compilation returned invalid JSON while running "
            f"{shlex.join(command)}\n{result.stderr}\n{result.stdout}".strip()
        ) from exc
    return CompiledMarimoPage.from_json(payload)


def uv_command() -> list[str]:
    if shutil.which("uv") is not None:
        return ["uv"]
    try:
        import uv  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Pages with pyproject metadata require uv. Install uv or use "
            "external-env in marimo-config."
        ) from exc
    return [sys.executable, "-m", "uv"]


@contextmanager
def compiler_environment() -> Generator[dict[str, str], None, None]:
    env = os.environ.copy()
    package_dir = Path(__file__).resolve().parent
    metadata_dir = package_distinfo()
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-import-") as temp_dir:
        import_root = Path(temp_dir)
        for source in (package_dir, metadata_dir):
            target = import_root / source.name
            try:
                target.symlink_to(source, target_is_directory=True)
            except OSError:
                shutil.copytree(source, target)
        paths = [str(import_root)]
        if pythonpath := env.get("PYTHONPATH"):
            paths.append(pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(paths)
        yield env


def package_distinfo() -> Path:
    dist = distribution("jupyter-book-marimo")
    for file in dist.files or ():
        root = file.parts[0] if file.parts else ""
        if root.endswith(".dist-info"):
            return Path(str(dist.locate_file(root)))

    root = Path(str(dist.locate_file("")))
    normalized_name = dist.metadata["Name"].replace("-", "_").lower()
    version = getattr(dist, "version", None) or dist.metadata["Version"]
    candidate = root / f"{normalized_name}-{version}.dist-info"
    if candidate.is_dir():
        return candidate

    matches = [
        path
        for path in root.glob(f"{normalized_name}-*.dist-info")
        if path.name.removesuffix(".dist-info").rsplit("-", 1)[0].lower()
        == normalized_name
    ]
    if len(matches) == 1:
        return matches[0]
    raise RuntimeError("Could not locate jupyter-book-marimo package metadata")
