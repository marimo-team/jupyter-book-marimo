"""Register the MyST directives and page transform."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .authoring import (
    MARIMO_CELL_NODE,
    MARIMO_CONFIG_NODE,
    MARIMO_CONFIG_OPTION_SPECS,
    MARIMO_DIRECTIVE_OPTION_SPECS,
    SUPPORTED_LANGUAGES,
    cell_from_directive,
    config_from_directive,
)
from .document import collect_document, replace_document_nodes
from .projection import project_page
from .runner import run_page_compiler

TRANSFORM_NAME = "marimo-islands"
MARIMO_DIRECTIVE = "marimo"
MARIMO_CONFIG_DIRECTIVE = "marimo-config"

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
                "doc": "TOML script metadata when the pyproject option is set.",
            },
        },
    ],
    "transforms": [
        {
            "name": TRANSFORM_NAME,
            "doc": "Compile marimo cells and project them as hydrated islands.",
            "stage": "document",
        }
    ],
}


def directive_nodes(name: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if name == MARIMO_DIRECTIVE:
        cell = cell_from_directive(data)
        return [
            {
                "type": MARIMO_CELL_NODE,
                "value": cell.source,
                "options": cell.options,
                "position": cell.position,
            }
        ]
    if name == MARIMO_CONFIG_DIRECTIVE:
        config = config_from_directive(data)
        return [
            {
                "type": MARIMO_CONFIG_NODE,
                "config": config.to_json(),
                "position": directive_position(data),
            }
        ]
    raise ValueError(f"Unknown directive: {name}")


def transform_document(tree: dict[str, Any]) -> dict[str, Any]:
    document = collect_document(tree)
    if not document.cells:
        replace_document_nodes(
            tree,
            {node_id: None for node_id in document.config_node_ids},
        )
        return tree

    page = run_page_compiler(
        document.page_request(),
        external_env=document.config.external_env,
    )
    replace_document_nodes(tree, project_page(document, page))
    return tree


def directive_position(data: dict[str, Any]) -> dict[str, Any] | None:
    node = data.get("node")
    if not isinstance(node, dict):
        return None
    position = node.get("position")
    return dict(position) if isinstance(position, dict) else None


def declare_result(content: Any) -> None:
    json.dump(content, sys.stdout)
    raise SystemExit(0)


def main() -> None:
    parser = argparse.ArgumentParser()
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
        declare_result(transform_document(json.load(sys.stdin)))
    if args.role:
        raise NotImplementedError(args.role)
    declare_result(PLUGIN_SPEC)


if __name__ == "__main__":
    main()
