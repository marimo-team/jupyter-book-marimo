"""Collect one MyST document into one marimo page request."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .authoring import (
    MARIMO_CONFIG_NODE,
    Cell,
    PageConfig,
    cell_from_node,
    config_from_node,
)
from .protocol import MarimoCellRequest, MarimoPageMetadata, MarimoPageRequest


@dataclass(frozen=True)
class CollectedCell:
    node_id: int
    cell: Cell


@dataclass(frozen=True)
class CollectedDocument:
    config: PageConfig
    cells: tuple[CollectedCell, ...]
    config_node_ids: frozenset[int]

    def page_request(self) -> MarimoPageRequest:
        authored = tuple(
            item.cell.request(index) for index, item in enumerate(self.cells)
        )
        setup_cells = setup_cell_requests(self.config)
        identity = page_identity(
            metadata=MarimoPageMetadata(
                pyproject=self.config.pyproject,
                setup_cells=setup_cells,
            ),
            defaults=self.config.defaults,
            cells=authored,
        )
        digest = identity.rsplit(":", 1)[-1]
        return MarimoPageRequest(
            identity=identity,
            filename=f"jupyter-book-marimo-{digest}.md",
            metadata=MarimoPageMetadata(
                pyproject=self.config.pyproject,
                setup_cells=setup_cells,
            ),
            defaults=self.config.defaults,
            cells=authored,
        )


def collect_document(tree: dict[str, Any]) -> CollectedDocument:
    cells: list[CollectedCell] = []
    config = PageConfig()
    config_node_ids: set[int] = set()

    def visit(node: dict[str, Any]) -> None:
        nonlocal config
        if node.get("type") == MARIMO_CONFIG_NODE:
            if config_node_ids:
                raise ValueError("Only one marimo-config directive is allowed per page")
            config = config_from_node(node)
            config_node_ids.add(id(node))

        cell = cell_from_node(node)
        if cell is not None:
            cells.append(CollectedCell(id(node), cell))

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    visit(child)

    visit(tree)
    return CollectedDocument(config, tuple(cells), frozenset(config_node_ids))


def replace_document_nodes(
    node: dict[str, Any],
    replacements: dict[int, dict[str, Any] | None],
) -> None:
    children = node.get("children")
    if not isinstance(children, list):
        return

    next_children: list[Any] = []
    for child in children:
        if isinstance(child, dict) and id(child) in replacements:
            replacement = replacements[id(child)]
            if replacement is not None:
                next_children.append(replacement)
            continue
        if isinstance(child, dict):
            replace_document_nodes(child, replacements)
        next_children.append(child)
    node["children"] = next_children


def setup_cell_requests(config: PageConfig) -> tuple[MarimoCellRequest, ...]:
    if not config.header.strip():
        return ()
    return (
        MarimoCellRequest(
            index=0,
            source=config.header,
            options={"language": "python"},
        ),
    )


def page_identity(
    *,
    metadata: MarimoPageMetadata,
    defaults: dict[str, Any],
    cells: tuple[MarimoCellRequest, ...],
) -> str:
    source = {
        "protocolVersion": 2,
        "metadata": {
            "pyproject": metadata.pyproject,
            "setupCells": [
                cell.to_json(include_position=False) for cell in metadata.setup_cells
            ],
        },
        "defaults": defaults,
        "cells": [cell.to_json(include_position=False) for cell in cells],
    }
    encoded = json.dumps(
        source,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"jupyter-book-marimo:{digest}"
