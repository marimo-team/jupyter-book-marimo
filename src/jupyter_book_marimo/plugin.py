"""Executable MyST plugin entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.resources import files
from pathlib import Path
from shutil import copyfileobj
from typing import Any

from .runtime import run_extractor
from .syntax import (
    Cell,
    CellOptions,
    SourcePage,
    code_cell_from_node,
    normalize_language,
    source_page,
)

WIDGET_CLASS = "marimo-jupyter-book-widget"
CONTAINER_WIDGET = "container-widget.mjs"

PLUGIN_SPEC = {
    "name": "Jupyter Book marimo",
    "directives": [],
    "transforms": [
        {
            "name": "marimo-code-fences",
            "doc": "Replace Python, SQL, and Markdown code fences marked with .marimo.",
            "stage": "document",
        }
    ],
}


def declare_result(content: Any) -> None:
    json.dump(content, sys.stdout)
    raise SystemExit(0)


def widget_esm() -> str:
    # MyST anywidget nodes need a browser-loadable ESM URL. The generated
    # directory gives Jupyter Book a same-origin copy of the packaged bridge.
    target_dir = Path.cwd() / ".jupyter-book-marimo"
    target_dir.mkdir(exist_ok=True)
    target = target_dir / CONTAINER_WIDGET
    source = files("jupyter_book_marimo.assets").joinpath(CONTAINER_WIDGET)
    with source.open("rb") as source_file:
        if not target.exists() or target.read_bytes() != source_file.read():
            source_file.seek(0)
            with target.open("wb") as target_file:
                copyfileobj(source_file, target_file)
    return f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"


def output_node(
    output: Any, index: int, source: str, position: dict[str, Any] | None
) -> dict[str, Any]:
    if not isinstance(output, dict) or not isinstance(output.get("html"), str):
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
        return {
            "type": "code",
            "lang": "text",
            "value": f"Missing marimo output {index} ({digest})",
            "position": position,
        }
    return {
        "type": "anywidget",
        "esm": widget_esm(),
        "model": output,
        "class": WIDGET_CLASS,
        "position": position,
    }


def collect_document(
    tree: dict[str, Any],
) -> tuple[dict[str, str], list[tuple[int, Cell]]]:
    metadata, source_lookup = source_page_context(tree)
    cells: list[tuple[int, Cell]] = []

    def visit(node: dict[str, Any]) -> None:
        cell = code_cell_from_node(node, source_options_for_node(node, source_lookup))
        if cell is not None:
            cells.append((id(node), cell))

        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child)

    visit(tree)
    return metadata, cells


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


def code_signature(node: dict[str, Any]) -> tuple[int, str, str] | None:
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


def code_signatures(tree: dict[str, Any]) -> set[tuple[int, str, str]]:
    signatures: set[tuple[int, str, str]] = set()

    def visit(node: dict[str, Any]) -> None:
        signature = code_signature(node)
        if signature is not None:
            signatures.add(signature)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child)

    visit(tree)
    return signatures


def source_fence_lookup(
    tree: dict[str, Any] | None = None,
) -> dict[tuple[int, str, str], CellOptions]:
    return source_page_context(tree)[1]


def source_page_context(
    tree: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[tuple[int, str, str], CellOptions]]:
    signatures = code_signatures(tree) if tree is not None else None
    best: SourcePage | None = None
    best_score = 0

    lookup: dict[tuple[int, str, str], CellOptions] = {}
    for path in source_files(Path.cwd()):
        try:
            source = path.read_text()
        except OSError:
            continue
        page = source_page(source)
        if signatures is not None:
            score = sum(
                (fence.start_line, fence.language, fence.code) in signatures
                for fence in page.fences
            )
            if score > best_score:
                best = page
                best_score = score
            elif score == best_score and score > 0:
                best = None
            continue
        for fence in page.fences:
            lookup[(fence.start_line, fence.language, fence.code)] = fence.options
    if signatures is not None:
        for fence in best.fences if best is not None else ():
            lookup[(fence.start_line, fence.language, fence.code)] = fence.options
        return (best.metadata if best is not None else {}), lookup
    return {}, lookup


def source_options_for_node(
    node: dict[str, Any], lookup: dict[tuple[int, str, str], CellOptions]
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


def run_transform(name: str, tree: dict[str, Any]) -> dict[str, Any]:
    if name != "marimo-code-fences":
        raise ValueError(f"Unknown transform: {name}")

    metadata, indexed_cells = collect_document(tree)
    cells = [cell for _, cell in indexed_cells]
    if not cells:
        replace_nodes(tree, {})
        return tree

    payload = {
        "file": synthetic_filename(cells),
        "source": "",
        "metadata": metadata,
        "cells": [cell.payload() for cell in cells],
    }
    page = run_extractor(payload)
    outputs = page.get("outputs") if isinstance(page, dict) else []
    replacements = {
        node_id: output_node(
            outputs[index]
            if isinstance(outputs, list) and index < len(outputs)
            else None,
            index,
            cell.code,
            cell.position,
        )
        for index, (node_id, cell) in enumerate(indexed_cells)
    }
    replace_nodes(tree, replacements)
    return tree


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role")
    group.add_argument("--directive")
    group.add_argument("--transform")
    args = parser.parse_args()

    if args.directive:
        raise NotImplementedError(args.directive)
    if args.transform:
        declare_result(run_transform(args.transform, json.load(sys.stdin)))
    if args.role:
        raise NotImplementedError(args.role)
    declare_result(PLUGIN_SPEC)


if __name__ == "__main__":
    main()
