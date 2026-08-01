"""Register the MyST executable plugin and transform marimo document nodes.

Jupyter Book calls this module to discover directives and run the document
transform. The transform collects `{marimo}` cells, resolves page source
context, invokes the extractor once, and replaces each cell node with an
anywidget node.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from shutil import copyfileobj
from typing import Any
from urllib.parse import unquote, urlparse

from .authoring import (
    MARIMO_CELL_NODE,
    MARIMO_CONFIG_NODE,
    MARIMO_CONFIG_OPTION_SPECS,
    MARIMO_DIRECTIVE_OPTION_SPECS,
    SUPPORTED_LANGUAGES,
    Cell,
    cell_from_directive,
    cell_from_node,
    config_from_directive,
)
from .runtime import run_extractor

TRANSFORM_NAME = "marimo-islands"
MARIMO_DIRECTIVE = "marimo"
MARIMO_CONFIG_DIRECTIVE = "marimo-config"
STYLESHEETS_ENV = "JUPYTER_BOOK_MARIMO_STYLESHEETS"
WIDGET_CLASS = "marimo-jupyter-book-widget"
CONTAINER_WIDGET = "container-widget.mjs"
GENERATED_DIR = ".jupyter-book-marimo"

PLUGIN_SPEC = {
    "name": "Jupyter Book marimo",
    "directives": [
        {
            "name": MARIMO_DIRECTIVE,
            "doc": "Execute a marimo cell.",
            "arg": {
                "type": "string",
                "required": True,
                "doc": "Cell language: " + ", ".join(sorted(SUPPORTED_LANGUAGES)) + ".",
            },
            "options": MARIMO_DIRECTIVE_OPTION_SPECS,
            "body": {
                "type": "string",
                "required": True,
                "doc": "Cell source code.",
            },
        },
        {
            "name": MARIMO_CONFIG_DIRECTIVE,
            "doc": "Configure marimo execution for the current page.",
            "options": MARIMO_CONFIG_OPTION_SPECS,
            "body": {
                "type": "string",
                "required": False,
                "doc": "TOML pyproject metadata when the pyproject option is set.",
            },
        },
    ],
    "transforms": [
        {
            "name": TRANSFORM_NAME,
            "doc": "Replace marimo directive nodes with hydrated anywidgets.",
            "stage": "document",
        }
    ],
}


@dataclass(frozen=True)
class CollectedCell:
    node_id: int
    cell: Cell


@dataclass(frozen=True)
class CollectedDocument:
    metadata: dict[str, Any]
    source_path: Path | None
    indexed_cells: list[CollectedCell]
    config_node_ids: set[int]
    config_ranges: list[dict[str, int]]

    @property
    def cells(self) -> list[Cell]:
        return [item.cell for item in self.indexed_cells]

    def payload(self) -> dict[str, Any]:
        cells = self.cells
        return {
            "file": str(self.source_path or synthetic_filename(cells)),
            "identity": source_identity(self.source_path, cells),
            "source": source_text(self.source_path),
            "metadata": self.metadata,
            "cells": [cell_payload(cell) for cell in cells],
            "sourceRanges": {"config": self.config_ranges},
        }


def source_files(root: Path) -> list[Path]:
    ignored = {
        ".git",
        ".jupyter-book-marimo",
        ".venv",
        "_build",
        "_site",
        "dist",
        "nogit",
        "__pycache__",
    }
    return [
        path
        for path in root.rglob("*.md")
        if not any(part in ignored for part in path.parts)
    ]


def source_path_for_cells(
    cells: list[Cell],
    *,
    root: Path | None = None,
) -> Path | None:
    """Locate the current source page by matching parsed directive bodies.

    MyST executable transforms pass node positions without a source filename. The
    extractor uses the resolved page path for app IDs, Molab export, and relative file
    access.
    """
    if not cells:
        return None

    search_root = (root or Path.cwd()).resolve()
    best_paths: list[Path] = []
    best_score = 0
    for path in source_files(search_root):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        score = sum(1 for cell in cells if cell.code and cell.code in source)
        if score > best_score:
            best_paths = [path]
            best_score = score
        elif score == best_score and score > 0:
            best_paths.append(path)

    if len(best_paths) > 1:
        return None
    return best_paths[0] if best_paths else None


def synthetic_filename(cells: list[Cell]) -> str:
    """Create a stable fallback filename when MyST gives no source path."""
    body = "\n\n".join(cell.code for cell in cells)
    digest = hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]
    return f"jupyter-book-marimo-{digest}.md"


def book_source_root(path: Path | None) -> Path:
    """Return the book source root for a resolved source page."""
    if path is None:
        return Path.cwd()
    for parent in (path.parent, *path.parents):
        if (parent / "myst.yml").exists() or (parent / "_toc.yml").exists():
            return parent
    return Path.cwd()


def source_identity(path: Path | None, cells: list[Cell]) -> str:
    """Prefer a repo-relative page identity so browser app IDs are stable."""
    if path is None:
        return synthetic_filename(cells)
    try:
        return path.relative_to(book_source_root(path)).as_posix()
    except ValueError:
        return path.as_posix()


def source_text(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def source_range(position: dict[str, Any] | None) -> dict[str, int] | None:
    if position is None:
        return None
    start_line = (position.get("start") or {}).get("line")
    end_line = (position.get("end") or {}).get("line")
    if isinstance(start_line, int) and isinstance(end_line, int):
        return {"startLine": start_line, "endLine": end_line}
    return None


def cell_payload(cell: Cell) -> dict[str, Any]:
    payload = cell.payload()
    if (cell_range := source_range(cell.position)) is not None:
        payload.update(cell_range)
    return payload


def safe_asset_stem(path: Path) -> str:
    stem = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-" for char in path.stem
    ).strip("-_")
    return stem or "style"


def is_external_stylesheet(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def is_file_stylesheet(value: str) -> bool:
    return value.startswith("file://")


def file_stylesheet_path(stylesheet: str) -> Path:
    parsed = urlparse(stylesheet)
    path = unquote(parsed.path)
    if os.name == "nt":
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            path = f"//{parsed.netloc}{path}"
        elif len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
    return Path(path).expanduser()


def embedded_style_block(source: Path) -> dict[str, str]:
    if not source.is_file():
        raise ValueError(f"Custom stylesheet is not a file: {source}")

    content = source.read_text(encoding="utf-8")
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    return {"id": f"{safe_asset_stem(source)}-{digest}", "css": content}


def custom_style_asset(stylesheet: str) -> tuple[str | None, dict[str, str] | None]:
    """Resolve a custom stylesheet into a served href or embedded CSS block.

    External URLs and root-relative book paths stay as hrefs. Local files are
    embedded into the widget model so the bridge can inject them into marimo
    shadow roots from the same model payload.
    """
    if not stylesheet:
        raise ValueError("Stylesheet path cannot be empty")

    if is_external_stylesheet(stylesheet):
        return stylesheet, None
    if is_file_stylesheet(stylesheet):
        source = file_stylesheet_path(stylesheet)
        if not source.exists():
            raise FileNotFoundError(f"Custom stylesheet not found: {stylesheet}")
        return None, embedded_style_block(source)
    if stylesheet.startswith("/"):
        if (source := Path(stylesheet)).exists():
            return None, embedded_style_block(source)
        return stylesheet, None
    source = Path(stylesheet).expanduser()
    source = Path.cwd() / source
    if not source.exists():
        raise FileNotFoundError(f"Custom stylesheet not found: {stylesheet}")
    return None, embedded_style_block(source)


def custom_style_assets(
    stylesheets: tuple[str, ...] = (),
) -> tuple[list[str], list[dict[str, str]]]:
    seen_hrefs: set[str] = set()
    seen_blocks: set[str] = set()
    hrefs: list[str] = []
    style_blocks: list[dict[str, str]] = []

    for stylesheet in stylesheets:
        href, style_block = custom_style_asset(stylesheet)
        if href is not None and href not in seen_hrefs:
            seen_hrefs.add(href)
            hrefs.append(href)
        if style_block is not None and style_block["id"] not in seen_blocks:
            seen_blocks.add(style_block["id"])
            style_blocks.append(style_block)
    return hrefs, style_blocks


def stylesheets_from_env() -> tuple[str, ...]:
    raw = os.environ.get(STYLESHEETS_ENV, "").strip()
    if not raw:
        return ()
    if raw.startswith("["):
        values = json.loads(raw)
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise ValueError(f"{STYLESHEETS_ENV} must be a JSON string list")
        return tuple(value for value in values if value.strip())
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def generated_dir(source_path: Path | None = None) -> Path:
    target_dir = book_source_root(source_path) / GENERATED_DIR
    target_dir.mkdir(exist_ok=True)
    return target_dir


def generated_asset_url(filename: str) -> str:
    """Return the source-relative asset URL consumed by MyST."""
    return f"/{GENERATED_DIR}/{filename}"


def widget_esm(source_path: Path | None = None) -> str:
    """Copy the packaged bridge into the book and return its ESM URL."""
    target_dir = generated_dir(source_path)
    target = target_dir / CONTAINER_WIDGET
    source = files("jupyter_book_marimo.assets").joinpath(CONTAINER_WIDGET)
    with source.open("rb") as source_file:
        if not target.exists() or target.read_bytes() != source_file.read():
            source_file.seek(0)
            with target.open("wb") as target_file:
                copyfileobj(source_file, target_file)
    return generated_asset_url(CONTAINER_WIDGET)


def output_node(
    output: Any,
    index: int,
    source: str,
    position: dict[str, Any] | None,
    source_path: Path | None = None,
    custom_stylesheets: list[str] | None = None,
    custom_style_blocks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Return the MyST anywidget node for one extractor output."""
    if not isinstance(output, dict) or not isinstance(output.get("html"), str):
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
        raise RuntimeError(f"Missing marimo output {index} ({digest})")

    model = dict(output)
    if custom_stylesheets:
        model["customStylesheets"] = custom_stylesheets
    if custom_style_blocks:
        model["customStyleBlocks"] = custom_style_blocks
    widget_id_digest = hashlib.sha1(
        f"{model.get('appId', '')}\0{index}\0{source}".encode()
    ).hexdigest()[:12]
    return {
        "type": "anywidget",
        "id": f"jupyter-book-marimo-{index}-{widget_id_digest}",
        "esm": widget_esm(source_path),
        "model": model,
        "class": WIDGET_CLASS,
        "position": position,
    }


def collect_document(
    tree: dict[str, Any],
) -> CollectedDocument:
    cells: list[CollectedCell] = []
    config: dict[str, Any] = {}
    config_node_ids: set[int] = set()
    config_ranges: list[dict[str, int]] = []

    def visit(node: dict[str, Any]) -> None:
        if node.get("type") == MARIMO_CONFIG_NODE:
            if config_node_ids:
                raise ValueError("Only one marimo-config directive is allowed per page")
            config.update(dict(node.get("options") or {}))
            config_node_ids.add(id(node))
            position = node.get("position")
            if isinstance(position, dict):
                if (config_range := source_range(position)) is not None:
                    config_ranges.append(config_range)

        cell = cell_from_node(node)
        if cell is not None:
            cells.append(CollectedCell(id(node), cell))

        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child)

    visit(tree)
    return CollectedDocument(
        config,
        source_path_for_cells([item.cell for item in cells]),
        cells,
        config_node_ids,
        config_ranges,
    )


def replace_nodes(
    node: dict[str, Any], replacements: dict[int, dict[str, Any] | None]
) -> None:
    children = node.get("children")
    if not isinstance(children, list):
        return

    new_children: list[Any] = []
    for child in children:
        if isinstance(child, dict) and id(child) in replacements:
            replacement = replacements[id(child)]
            if replacement is not None:
                new_children.append(replacement)
            continue
        if isinstance(child, dict):
            replace_nodes(child, replacements)
        new_children.append(child)
    node["children"] = new_children


def transform_document(
    tree: dict[str, Any],
    *,
    stylesheets: tuple[str, ...] = (),
) -> dict[str, Any]:
    document = collect_document(tree)
    if not document.cells:
        replace_nodes(tree, {node_id: None for node_id in document.config_node_ids})
        return tree

    page = run_extractor(document.payload())
    outputs = page.get("outputs") if isinstance(page, dict) else []
    if not isinstance(outputs, list) or len(outputs) != len(document.indexed_cells):
        raise RuntimeError(
            "marimo extractor returned "
            f"{len(outputs) if isinstance(outputs, list) else 'no'} outputs for "
            f"{len(document.indexed_cells)} cells"
        )
    custom_stylesheets, custom_style_blocks = custom_style_assets(stylesheets)
    replacements: dict[int, dict[str, Any] | None] = {
        node_id: None for node_id in document.config_node_ids
    }
    for index, item in enumerate(document.indexed_cells):
        replacements[item.node_id] = output_node(
            outputs[index],
            index,
            item.cell.code,
            item.cell.position,
            document.source_path,
            custom_stylesheets,
            custom_style_blocks,
        )
    replace_nodes(tree, replacements)
    return tree


def declare_result(content: Any) -> None:
    """Keep the executable-plugin protocol to one JSON value on stdout."""
    json.dump(content, sys.stdout)
    raise SystemExit(0)


def configured_stylesheets(styles: list[str]) -> tuple[str, ...]:
    return (*stylesheets_from_env(), *tuple(styles))


def directive_nodes(name: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if name == MARIMO_DIRECTIVE:
        cell = cell_from_directive(data)
        return [
            {
                "type": MARIMO_CELL_NODE,
                "language": cell.options["language"],
                "value": cell.code,
                "options": cell.options,
                "position": cell.position,
            }
        ]
    if name == MARIMO_CONFIG_DIRECTIVE:
        return [
            {
                "type": MARIMO_CONFIG_NODE,
                "options": config_from_directive(data),
                "position": (data.get("node") or {}).get("position")
                if isinstance(data.get("node"), dict)
                else None,
            }
        ]
    raise ValueError(f"Unknown directive: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--style",
        action="append",
        default=[],
        help=(
            "Custom stylesheet path or URL to inject into marimo output. "
            "Repeat for multiple stylesheets."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role")
    group.add_argument("--directive")
    group.add_argument("--transform")
    args = parser.parse_args()

    if args.directive:
        declare_result(directive_nodes(args.directive, json.load(sys.stdin)))
    if args.transform:
        if args.transform != TRANSFORM_NAME:
            raise ValueError(f"Unknown transform: {args.transform}")
        declare_result(
            transform_document(
                json.load(sys.stdin),
                stylesheets=configured_stylesheets(args.style),
            )
        )
    if args.role:
        raise NotImplementedError(args.role)
    declare_result(PLUGIN_SPEC)


if __name__ == "__main__":
    main()
