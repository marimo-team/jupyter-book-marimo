"""Run page extraction in-process, in the caller environment, or through uv.

The plugin sends one JSON payload per page and expects JSON on stdout. Runtime helpers
wrap the marimo-private hooks used to build browser-ready islands.
"""

from __future__ import annotations

import ast
import asyncio
from collections.abc import Generator
from contextlib import contextmanager, redirect_stdout
import hashlib
from html.parser import HTMLParser
import importlib
from importlib.metadata import distribution
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
import tempfile
from typing import Any, TypeGuard

from .authoring import as_bool, pyproject_to_script_metadata

MARIMO_REQUIREMENT = "marimo>=0.23.8"

UV_RUN_TIMEOUT_SECONDS = int(
    os.environ.get("JUPYTER_BOOK_MARIMO_UV_TIMEOUT_SECONDS", "300")
)


def page_digest(filename: str) -> str:
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]


def page_cell_prefix(filename: str) -> str:
    return f"jb{page_digest(filename)}"


class HeadAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.module_scripts: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "script" and values.get("type") == "module" and values.get("src"):
            self.module_scripts.append(values["src"])
        elif tag == "link" and values.get("href"):
            self.links.append(values)


def build_export_notebook_code(
    generator: Any,
    pyproject: str,
) -> str:
    from marimo._session.notebook import AppFileManager

    notebook_code = AppFileManager.from_app(generator._app).to_code()
    notebook_code = hoist_future_imports(notebook_code)
    script_metadata = pyproject_to_script_metadata(pyproject)
    if script_metadata:
        notebook_code = f"{script_metadata}{notebook_code}"
    return notebook_code


def hoist_future_imports(notebook_code: str) -> str:
    try:
        tree = ast.parse(notebook_code)
    except SyntaxError as exc:
        raise RuntimeError(
            "Could not parse exported notebook code while hoisting future imports"
        ) from exc
    lines = notebook_code.splitlines(keepends=True)
    future_nodes = sorted(
        (node for node in ast.walk(tree) if is_future_import(node)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    hoisted_imports: list[str] = []
    for node in future_nodes:
        source = future_import_source(notebook_code, node)
        if source not in hoisted_imports:
            hoisted_imports.append(source)

    remove_ranges = [
        (node.lineno - 1, node.end_lineno or node.lineno) for node in future_nodes
    ]

    if not remove_ranges:
        return notebook_code

    for start, end in sorted(remove_ranges, reverse=True):
        del lines[start:end]

    if hoisted_imports:
        original_insert_at = future_import_insert_index(tree)
        removed_before_insert = sum(
            end - start for start, end in remove_ranges if start < original_insert_at
        )
        insert_at = max(0, original_insert_at - removed_before_insert)
        insertion = "\n".join(hoisted_imports) + "\n"
        if insert_at < len(lines) and lines[insert_at].strip():
            insertion += "\n"
        lines.insert(insert_at, insertion)

    return "".join(lines)


def is_future_import(node: ast.AST) -> TypeGuard[ast.ImportFrom]:
    return isinstance(node, ast.ImportFrom) and node.module == "__future__"


def future_import_source(notebook_code: str, node: ast.ImportFrom) -> str:
    source = ast.get_source_segment(notebook_code, node)
    if source is None:
        source = notebook_code.splitlines()[node.lineno - 1]
    source = dedent(source).strip()
    lines = source.splitlines()
    if len(lines) > 1:
        indentation = min(
            len(line) - len(line.lstrip()) for line in lines[1:] if line.strip()
        )
        if indentation:
            lines = [
                lines[0],
                *[
                    line[indentation:] if len(line) >= indentation else line
                    for line in lines[1:]
                ],
            ]
            source = "\n".join(lines)
    return source


def future_import_insert_index(tree: ast.Module) -> int:
    insert_at = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insert_at = tree.body[0].end_lineno or tree.body[0].lineno
    return insert_at


def storage() -> Any:
    from marimo._session.notebook.storage import FilesystemStorage

    class Storage(FilesystemStorage):
        def write(self, path: Path, content: str) -> None:  # noqa: ARG002
            return None

        def rename(self, old_path: Path, new_path: Path) -> None:  # noqa: ARG002
            return None

    return Storage()


class Runtime:
    def __init__(self, *, app_id: str, cell_prefix: str) -> None:
        from marimo import MarimoIslandGenerator
        from marimo._ast.cell_manager import CellManager

        self.generator = MarimoIslandGenerator(app_id=app_id)
        self.generator._app._app._cell_manager = CellManager(prefix=cell_prefix)

    def apply_cell_metadata(self, stub: Any, plan: Any) -> None:
        from marimo._ast.cell import CellConfig

        manager = self.generator._app.cell_manager
        cell_id = stub._cell_id
        cell = manager._compiled_cells.get(cell_id)
        notebook_cell = manager.document.get_cell(cell_id)

        config = CellConfig(
            column=plan.column,
            disabled=plan.disabled,
            hide_code=plan.hide_code,
        )
        notebook_cell.config = config
        if cell is not None:
            cell._cell.configure(config)

        if plan.name:
            notebook_cell.name = plan.name
            if cell is not None:
                cell._name = plan.name

    async def build(self, filename: str) -> bool:
        from marimo._server.export import run_app_until_completion
        from marimo._session.notebook import AppFileManager

        if self.generator.has_run:
            raise ValueError("marimo generator can only be built once")

        manager = AppFileManager.from_app(self.generator._app)
        manager.storage = storage()
        manager.filename = filename
        manager.app._app._filename = filename
        session, did_error = await run_app_until_completion(
            file_manager=manager,
            cli_args={},
            argv=None,
            persist_session=False,
        )
        self.generator.has_run = True

        for stub in self.generator._stubs:
            stub._internal_app = self.generator._app
            stub._session_view = session
        return did_error

    def export_notebook_code(self, pyproject: str) -> str:
        return build_export_notebook_code(self.generator, pyproject)

    def render_assets(self) -> dict[str, Any]:
        import marimo

        parser = HeadAssetParser()
        parser.feed(self.generator.render_head(version_override=marimo.__version__))
        return {
            "version": marimo.__version__,
            "moduleScripts": parser.module_scripts,
            "links": parser.links,
        }


async def extract(payload: dict[str, Any]) -> dict[str, Any]:
    """Import the extractor only when execution is requested."""
    from .extract import extract as real_extract

    return await real_extract(payload)


def initialize_marimo_asyncio() -> None:
    """Install the event-loop policy required by marimo sessions."""
    from marimo._utils.asyncio_utils import initialize_asyncio

    initialize_asyncio()


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def distinfo() -> Path:
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

    matches: list[Path] = []
    for path in root.glob(f"{normalized_name}-*.dist-info"):
        stem = path.name.removesuffix(".dist-info").lower()
        package_name = stem.rsplit("-", 1)[0]
        if package_name == normalized_name:
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    raise RuntimeError("Could not locate jupyter-book-marimo package metadata")


def uv_command() -> list[str]:
    if shutil.which("uv") is not None:
        return ["uv"]
    try:
        import uv  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "jupyter-book-marimo uses uv for pages with :pyproject: metadata. "
            "Install uv or set :external-env: true for this page."
        ) from exc
    return [sys.executable, "-m", "uv"]


@contextmanager
def sandbox_env() -> Generator[dict[str, str], None, None]:
    """Expose this package to uv without exporting the caller's import path."""
    env = os.environ.copy()
    package_dir = Path(__file__).resolve().parent
    metadata_dir = distinfo()
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-import-") as temp_dir:
        import_root = Path(temp_dir)
        for source in (package_dir, metadata_dir):
            target = import_root / source.name
            try:
                target.symlink_to(source, target_is_directory=True)
            except OSError:
                shutil.copytree(source, target)
        pythonpath = env.get("PYTHONPATH")
        paths = [str(import_root)]
        if pythonpath:
            paths.append(pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(paths)
        yield env


@contextmanager
def uv_run_args(pyproject: str = "") -> Generator[list[str], None, None]:
    # marimo moved sandbox helpers across private modules. Support both import
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

    script_metadata = pyproject_to_script_metadata(pyproject or "dependencies = []")
    pyproject_config = pyproject_reader.from_script(script_metadata)
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-") as temp_dir:
        # construct_uv_flags writes requirements/constraints beside this file.
        # keep that scratch state scoped to one page extraction.
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=temp_dir, suffix=".txt"
        ) as temp_file:
            flags = sandbox_module.construct_uv_flags(
                pyproject_config,
                temp_file,
                [],
                [MARIMO_REQUIREMENT],
            )
            temp_file.flush()
        yield ["run", *flags]  # type: ignore[misc]


def run_extractor_process(
    command: list[str],
    payload: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            timeout=UV_RUN_TIMEOUT_SECONDS,
            env=env,
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


def run_extractor(payload: dict[str, Any]) -> dict[str, Any]:
    """Run extraction through the environment requested by page metadata."""
    metadata = payload.get("metadata")
    document_options = metadata if isinstance(metadata, dict) else {}
    if as_bool(document_options.get("external_env")):
        command = [sys.executable, "-m", "jupyter_book_marimo.extract"]
        return run_extractor_process(command, payload, env=os.environ.copy())

    pyproject = document_options.get("pyproject")
    if not isinstance(pyproject, str) or not pyproject.strip():
        initialize_marimo_asyncio()
        with redirect_stdout(sys.stderr):
            return asyncio.run(extract(payload))

    with uv_run_args(pyproject if isinstance(pyproject, str) else "") as args:
        args.extend(["python", "-m", "jupyter_book_marimo.extract"])
        command = [*uv_command(), *args]
        with sandbox_env() as env:
            return run_extractor_process(command, payload, env=env)
