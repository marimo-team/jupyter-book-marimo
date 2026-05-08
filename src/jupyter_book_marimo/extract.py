#!/usr/bin/env python3
"""Execute page-level marimo cells for the Jupyter Book plugin."""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from textwrap import dedent
from typing import Any

import marimo
from marimo import MarimoIslandGenerator
from marimo._ast.cell_manager import CellManager
from marimo._convert.common.format import markdown_to_marimo, sql_to_marimo
from marimo._session.notebook import AppFileManager
from marimo._session.notebook.storage import FilesystemStorage

MIN_MARIMO_VERSION = "0.23.5"


def version_tuple(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        return (0, 0, 0)
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


if version_tuple(marimo.__version__) < version_tuple(MIN_MARIMO_VERSION):
    raise RuntimeError(
        f"jupyter-book-marimo requires marimo >= {MIN_MARIMO_VERSION}, "
        f"got {marimo.__version__}"
    )


class ReadOnlyFilesystemStorage(FilesystemStorage):
    """Let marimo read source-relative files without rewriting book sources."""

    def write(self, path: Path, content: str) -> None:  # noqa: ARG002
        return None

    def rename(self, old_path: Path, new_path: Path) -> None:  # noqa: ARG002
        return None


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


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def normalized_options(options: dict[str, Any]) -> dict[str, Any]:
    return {key.replace("-", "_"): value for key, value in options.items()}


def source_for_cell(cell: dict[str, Any]) -> str:
    options = normalized_options(cell.get("options") or {})
    code = str(cell.get("code") or "")
    language = str(options.get("language") or "python").lower()

    if language == "sql":
        return sql_to_marimo(
            code,
            str(options.get("query") or "_df"),
            as_bool(options.get("hide_output")),
            options.get("engine"),
        )
    if language in {"markdown", "md"}:
        return markdown_to_marimo(code)
    return code


def visible_code_html(code: str, language: str, message: str | None = None) -> str:
    escaped = html.escape(code)
    note = (
        f'<div class="marimo-plugin-note">{html.escape(message)}</div>'
        if message
        else ""
    )
    return (
        '<div class="marimo-plugin-fallback">'
        f'{note}<pre><code class="language-{html.escape(language)}">'
        f"{escaped}</code></pre></div>"
    )


def use_browser_cell_index(island: str, cell_index: int) -> str:
    """Use browser-local cell indexes for reactive islands.

    The server export and the browser Pyodide runtime do not share generated
    cell IDs. marimo islands can instead resolve cells by index after the
    runtime loads the notebook code.
    """
    return re.sub(
        r'\s+data-cell-id="[^"]+"',
        f'\n    data-cell-idx="{cell_index}"',
        island,
        count=1,
    )


def output_model(
    html: str,
    *,
    app_id: str = "",
    notebook_code: str = "",
    assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model: dict[str, Any] = {"html": html}
    if app_id:
        model["appId"] = app_id
    if notebook_code:
        model["notebookCode"] = notebook_code
    if assets:
        model["assets"] = assets
    return model


def page_digest(filename: str) -> str:
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]


def page_cell_prefix(filename: str) -> str:
    return f"jb{page_digest(filename)}"


def pyproject_to_script_metadata(pyproject: str) -> str:
    body = dedent(pyproject).strip()
    if not body:
        return ""
    if body.startswith("# /// script"):
        return f"{body}\n"

    commented_lines = ["# /// script"]
    for line in body.splitlines():
        commented_lines.append(f"# {line}" if line else "#")
    commented_lines.append("# ///")
    return "\n".join(commented_lines) + "\n"


def build_export_notebook_code(
    generator: MarimoIslandGenerator,
    pyproject: str,
    *,
    cell_prefix: str,
    header: str = "",
) -> str:
    notebook_code = AppFileManager.from_app(generator._app).to_code()
    notebook_code = install_browser_cell_prefix(notebook_code, cell_prefix)
    header = dedent(header).strip()
    script_metadata = pyproject_to_script_metadata(pyproject)
    if header:
        notebook_code = f"{header}\n\n{notebook_code}"
    if script_metadata:
        notebook_code = f"{script_metadata}{notebook_code}"
    return notebook_code


def install_browser_cell_prefix(notebook_code: str, cell_prefix: str) -> str:
    """Make browser-generated cell IDs match the server export."""
    import_line = "from marimo._ast.cell_manager import CellManager\n"
    if import_line not in notebook_code:
        notebook_code = notebook_code.replace(
            "import marimo\n",
            f"import marimo\n{import_line}",
            1,
        )
    updated = notebook_code.replace(
        "app = marimo.App()\n",
        f'app = marimo.App()\napp._cell_manager = CellManager(prefix="{cell_prefix}")\n',
        1,
    )
    if updated == notebook_code:
        raise ValueError("Could not install browser cell prefix in marimo code")
    return updated


def render_assets(generator: MarimoIslandGenerator) -> dict[str, Any]:
    parser = HeadAssetParser()
    parser.feed(generator.render_head(version_override=marimo.__version__))
    return {
        "moduleScripts": parser.module_scripts,
        "links": parser.links,
    }


async def build_generator(generator: MarimoIslandGenerator, filename: str) -> None:
    from marimo._server.export import run_app_until_completion

    if generator.has_run:
        raise ValueError("marimo generator can only be built once")

    file_manager = AppFileManager.from_app(generator._app)
    file_manager.storage = ReadOnlyFilesystemStorage()
    file_manager.filename = filename
    file_manager.app._app._filename = filename
    session, _did_error = await run_app_until_completion(
        file_manager=file_manager,
        cli_args={},
        argv=None,
        persist_session=False,
    )
    generator.has_run = True

    for stub in generator._stubs:
        stub._internal_app = generator._app
        stub._session_view = session


async def extract(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    cells = payload.get("cells") or []
    filename = str(payload.get("file") or "")
    eval_enabled = metadata.get("eval") is not False
    app_id = "jb-" + page_digest(filename)
    generator = MarimoIslandGenerator(app_id=app_id)
    generator._app._app._cell_manager = CellManager(prefix=page_cell_prefix(filename))
    outputs: list[dict[str, Any]] = []
    executable_indexes: list[int] = []

    for index, cell in enumerate(cells):
        options = normalized_options(cell.get("options") or {})
        language = str(options.get("language") or "python").lower()
        code = source_for_cell(cell)
        display_code = (
            as_bool(options.get("echo")) or as_bool(options.get("editor"))
        ) and not as_bool(options.get("hide_code"))
        display_output = as_bool(options.get("output"), True) and not as_bool(
            options.get("hide_output")
        )
        include = as_bool(options.get("include"), True)
        disabled = as_bool(options.get("disabled"))
        unparseable = as_bool(options.get("unparseable")) or as_bool(
            options.get("unparsable")
        )

        if not include:
            outputs.append(output_model(""))
            continue

        if not eval_enabled or disabled or unparseable:
            message = None
            if disabled:
                message = "disabled"
            elif unparseable:
                message = "unparseable"
            outputs.append(
                output_model(
                    visible_code_html(code, language, message) if display_code else ""
                )
            )
            continue

        try:
            stub = generator.add_code(
                code,
                display_code=display_code,
                display_output=display_output,
                is_reactive=True,
                is_raw=True,
            )
        except Exception:
            if not display_code:
                raise
            outputs.append(
                output_model(
                    visible_code_html(
                        code,
                        language,
                        "could not compile",
                    )
                )
            )
            continue

        executable_indexes.append(index)
        outputs.append({"html": "", "_stub": stub})

    if executable_indexes:
        await build_generator(generator, filename)
        notebook_code = build_export_notebook_code(
            generator,
            str(metadata.get("pyproject") or ""),
            cell_prefix=page_cell_prefix(filename),
            header=str(metadata.get("header") or ""),
        )
        assets = render_assets(generator)
    else:
        notebook_code = ""
        assets = {}

    for cell_index, index in enumerate(executable_indexes):
        stub = outputs[index].pop("_stub")
        outputs[index] = output_model(
            use_browser_cell_index(stub.render(), cell_index),
            app_id=app_id,
            notebook_code=notebook_code,
            assets=assets,
        )

    return {
        "cells": [
            {"startLine": cell.get("startLine"), "options": cell.get("options") or {}}
            for cell in cells
        ],
        "outputs": outputs,
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    result = asyncio.run(extract(payload))
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
