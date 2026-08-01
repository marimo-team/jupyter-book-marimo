"""Build hidden runtime cells for page-level header code.

Headers run before authored cells and share the same browser cell index space.
The default `marimo as mo` import is added when generated SQL or Markdown cells need it.
Header errors fail the build.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from textwrap import dedent
from typing import Any

from marimo import MarimoIslandGenerator

from .island_output import has_error_mimetype, hide_island, use_browser_cell_index

DEFAULT_MARIMO_IMPORT = "import marimo as mo"


def header_source(header: str) -> str:
    return dedent(header).strip()


def source_imports_marimo_alias(source: str, name: str) -> bool:
    if not source.strip():
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "marimo" and (alias.asname or alias.name) == name:
                    return True
        if isinstance(node, ast.ImportFrom) and node.module == "marimo":
            if any((alias.asname or alias.name) == name for alias in node.names):
                return True
    return False


def source_uses_name(source: str, name: str) -> bool:
    if not source.strip():
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return bool(re.search(rf"\b{re.escape(name)}\b", source))

    return any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id == name
        for node in ast.walk(tree)
    )


def should_add_default_marimo_import(
    header: str,
    code_sources: Sequence[str],
    import_sources: Sequence[str] | None = None,
) -> bool:
    header_code = header_source(header)
    usage_sources = [header_code, *code_sources]
    alias_sources = [header_code, *(import_sources or code_sources)]
    return any(source_uses_name(source, "mo") for source in usage_sources) and not any(
        source_imports_marimo_alias(source, "mo") for source in alias_sources
    )


def runtime_header_sources(
    header: str,
    code_sources: list[str],
    import_sources: list[str] | None = None,
) -> tuple[str, ...]:
    source = header_source(header)
    sources: list[str] = []
    if should_add_default_marimo_import(header, code_sources, import_sources):
        sources.append(DEFAULT_MARIMO_IMPORT)
    if source:
        sources.append(source)
    return tuple(sources)


def add_header_cell(generator: MarimoIslandGenerator, header: str) -> Any | None:
    source = header_source(header)
    if not source:
        return None
    return generator.add_code(
        source,
        display_code=False,
        display_output=False,
        is_reactive=True,
        is_raw=True,
    )


def add_header_cells(
    generator: MarimoIslandGenerator,
    headers: tuple[str, ...],
) -> list[Any]:
    return [
        stub
        for header in headers
        if (stub := add_header_cell(generator, header)) is not None
    ]


def hidden_header_islands(header_stubs: list[Any]) -> str:
    return "".join(
        hide_island(
            use_browser_cell_index(
                header_stub.render(display_output=False),
                index,
            )
        )
        for index, header_stub in enumerate(header_stubs)
    )


def fail_on_header_errors(header_stubs: list[Any], filename: str) -> None:
    for header_index, header_stub in enumerate(header_stubs):
        header_html = use_browser_cell_index(
            header_stub.render(display_output=True),
            header_index,
        )
        if has_error_mimetype(header_html):
            raise RuntimeError(f"marimo execution failed in {filename}:header")
