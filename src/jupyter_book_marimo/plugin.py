"""Executable MyST plugin and document transform for marimo code fences."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
import os
from pathlib import Path
from shutil import copyfileobj
import sys
from typing import Any, NamedTuple

from .authoring import (
    Cell,
    CellOptions,
    SourcePage,
    code_cell_from_node,
    normalize_language,
    source_fences,
    source_page,
)
from .runtime import run_extractor

TRANSFORM_NAME = "marimo-code-fences"
STYLESHEETS_ENV = "JUPYTER_BOOK_MARIMO_STYLESHEETS"
WIDGET_CLASS = "marimo-jupyter-book-widget"
CONTAINER_WIDGET = "container-widget.mjs"
GENERATED_DIR = ".jupyter-book-marimo"

PLUGIN_SPEC = {
    "name": "Jupyter Book marimo",
    "directives": [],
    "transforms": [
        {
            "name": TRANSFORM_NAME,
            "doc": "Replace Python, SQL, and Markdown code fences marked with .marimo.",
            "stage": "document",
        }
    ],
}

CodeSignature = tuple[int, str, str]


class SourceContext(NamedTuple):
    metadata: dict[str, Any]
    options_by_signature: dict[CodeSignature, CellOptions]
    path: Path | None


@dataclass(frozen=True)
class CollectedCell:
    node_id: int
    cell: Cell


@dataclass(frozen=True)
class CollectedDocument:
    metadata: dict[str, Any]
    source_path: Path | None
    indexed_cells: list[CollectedCell]

    @property
    def cells(self) -> list[Cell]:
        return [item.cell for item in self.indexed_cells]

    def payload(self) -> dict[str, Any]:
        cells = self.cells
        return {
            "file": str(self.source_path or synthetic_filename(cells)),
            "identity": source_identity(self.source_path, cells),
            "source": "",
            "metadata": self.metadata,
            "cells": [cell.payload() for cell in cells],
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


def parsed_source_pages(root: Path) -> tuple[SourcePage, ...]:
    pages: list[SourcePage] = []
    for path in source_files(root):
        try:
            source = path.read_text()
        except OSError:
            continue
        pages.append(SourcePage(metadata={}, fences=source_fences(source), path=path))
    return tuple(pages)


def code_signature(node: dict[str, Any]) -> CodeSignature | None:
    if node.get("type") != "code":
        return None
    start = ((node.get("position") or {}).get("start") or {}).get("line")
    if not isinstance(start, int):
        return None
    return (
        start,
        normalize_language(str(node.get("lang") or "")),
        str(node.get("value") or ""),
    )


def code_signatures(tree: dict[str, Any]) -> set[CodeSignature]:
    signatures: set[CodeSignature] = set()

    def visit(node: dict[str, Any]) -> None:
        signature = code_signature(node)
        if signature is not None:
            signatures.add(signature)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child)

    visit(tree)
    return signatures


def source_page_context(
    tree: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    pages: tuple[SourcePage, ...] | None = None,
) -> SourceContext:
    signatures = code_signatures(tree) if tree is not None else None
    best_pages: list[SourcePage] = []
    best_score = 0

    lookup: dict[CodeSignature, CellOptions] = {}
    source_pages = (
        pages if pages is not None else parsed_source_pages(root or Path.cwd())
    )
    for page in source_pages:
        if signatures is not None:
            score = sum(
                (fence.start_line, fence.language, fence.code) in signatures
                for fence in page.fences
            )
            if score > best_score:
                best_pages = [page]
                best_score = score
            elif score == best_score and score > 0:
                best_pages.append(page)
            continue
        for fence in page.fences:
            lookup[(fence.start_line, fence.language, fence.code)] = fence.options
    if signatures is not None:
        if len(best_pages) > 1:
            paths = ", ".join(str(page.path) for page in best_pages)
            raise ValueError(
                f"Ambiguous marimo source page; matched multiple candidates: {paths}"
            )
        best = best_pages[0] if best_pages else None
        for fence in best.fences if best is not None else ():
            lookup[(fence.start_line, fence.language, fence.code)] = fence.options
        metadata: dict[str, Any] = best.metadata if best is not None else {}
        if best is not None and best.path is not None:
            source = best.path.read_text(encoding="utf-8")
            metadata = source_page(source, path=best.path).metadata
        return SourceContext(
            metadata,
            lookup,
            (best.path if best is not None else None),
        )
    return SourceContext({}, lookup, None)


def source_options_for_node(
    node: dict[str, Any], lookup: dict[CodeSignature, CellOptions]
) -> CellOptions | None:
    if node.get("type") != "code":
        return None
    start = ((node.get("position") or {}).get("start") or {}).get("line")
    if not isinstance(start, int):
        return None
    language = normalize_language(str(node.get("lang") or ""))
    code = str(node.get("value") or "")
    return lookup.get((start, language, code))


def synthetic_filename(cells: list[Cell]) -> str:
    body = "\n\n".join(cell.code for cell in cells)
    digest = hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]
    return f"jupyter-book-marimo-{digest}.md"


def source_identity(path: Path | None, cells: list[Cell]) -> str:
    if path is None:
        return synthetic_filename(cells)
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def safe_asset_stem(path: Path) -> str:
    stem = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-" for char in path.stem
    ).strip("-_")
    return stem or "style"


def is_external_stylesheet(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def custom_style_asset(stylesheet: str) -> tuple[str | None, dict[str, str] | None]:
    if not stylesheet:
        raise ValueError("Stylesheet path cannot be empty")

    source = Path(stylesheet).expanduser()
    if is_external_stylesheet(stylesheet):
        return stylesheet, None
    if stylesheet.startswith("/") and not source.exists():
        return stylesheet, None
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        raise FileNotFoundError(f"Custom stylesheet not found: {stylesheet}")
    if not source.is_file():
        raise ValueError(f"Custom stylesheet is not a file: {stylesheet}")

    content = source.read_text(encoding="utf-8")
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    return None, {"id": f"{safe_asset_stem(source)}-{digest}", "css": content}


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


def generated_dir() -> Path:
    target_dir = Path.cwd() / GENERATED_DIR
    target_dir.mkdir(exist_ok=True)
    return target_dir


def generated_asset_url(filename: str) -> str:
    return f"/{GENERATED_DIR}/{filename}"


def widget_esm() -> str:
    # MyST anywidget nodes need a browser-loadable ESM URL. The generated
    # directory gives Jupyter Book a same-origin copy of the packaged bridge.
    target_dir = generated_dir()
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
    custom_stylesheets: list[str] | None = None,
    custom_style_blocks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not isinstance(output, dict) or not isinstance(output.get("html"), str):
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
        return {
            "type": "code",
            "lang": "text",
            "value": f"Missing marimo output {index} ({digest})",
            "position": position,
        }

    model = dict(output)
    if custom_stylesheets:
        model["customStylesheets"] = custom_stylesheets
    if custom_style_blocks:
        model["customStyleBlocks"] = custom_style_blocks
    return {
        "type": "anywidget",
        "esm": widget_esm(),
        "model": model,
        "class": WIDGET_CLASS,
        "position": position,
    }


def collect_document(
    tree: dict[str, Any],
) -> CollectedDocument:
    context = source_page_context(tree)
    cells: list[CollectedCell] = []

    def visit(node: dict[str, Any]) -> None:
        cell = code_cell_from_node(
            node,
            source_options_for_node(node, context.options_by_signature),
        )
        if cell is not None:
            cells.append(CollectedCell(id(node), cell))

        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child)

    visit(tree)
    return CollectedDocument(context.metadata, context.path, cells)


def replace_nodes(
    node: dict[str, Any], replacements: dict[int, dict[str, Any]]
) -> None:
    children = node.get("children")
    if not isinstance(children, list):
        return

    new_children: list[Any] = []
    for child in children:
        if isinstance(child, dict) and id(child) in replacements:
            new_children.append(replacements[id(child)])
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
        replace_nodes(tree, {})
        return tree

    page = run_extractor(document.payload())
    outputs = page.get("outputs") if isinstance(page, dict) else []
    custom_stylesheets, custom_style_blocks = custom_style_assets(stylesheets)
    replacements = {
        item.node_id: output_node(
            outputs[index]
            if isinstance(outputs, list) and index < len(outputs)
            else None,
            index,
            item.cell.code,
            item.cell.position,
            custom_stylesheets,
            custom_style_blocks,
        )
        for index, item in enumerate(document.indexed_cells)
    }
    replace_nodes(tree, replacements)
    return tree


def declare_result(content: Any) -> None:
    json.dump(content, sys.stdout)
    raise SystemExit(0)


def configured_stylesheets(styles: list[str]) -> tuple[str, ...]:
    return (*stylesheets_from_env(), *tuple(styles))


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
        raise NotImplementedError(args.directive)
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
