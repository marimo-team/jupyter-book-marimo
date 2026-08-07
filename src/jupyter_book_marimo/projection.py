"""Project a compiled marimo page into MyST anywidget nodes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.resources import files
from pathlib import Path
from typing import Any

from .document import CollectedDocument
from .protocol import (
    CompiledMarimoCell,
    CompiledMarimoPage,
    JsonObject,
    project_page_cell_payloads,
)

GENERATED_DIR = ".jupyter-book-marimo"
WIDGET_ESM = "container-widget.mjs"
BRIDGE_CSS = "islands-bridge.css"


@dataclass(frozen=True)
class ProjectedAssets:
    esm: str
    css: str


def project_page(
    document: CollectedDocument,
    page: CompiledMarimoPage,
    *,
    root: Path | None = None,
) -> dict[int, dict[str, Any] | None]:
    validate_compiled_cells(document, page)
    assets = stage_assets(root=root)
    payloads = project_page_cell_payloads(page)

    replacements: dict[int, dict[str, Any] | None] = {
        node_id: None for node_id in document.config_node_ids
    }
    for item, cell, payload in zip(
        document.cells,
        page.cells,
        payloads,
        strict=True,
    ):
        replacements[item.node_id] = (
            anywidget_node(
                cell,
                payload,
                item.cell.position,
                assets,
            )
            if payload is not None
            else None
        )
    return replacements


def validate_compiled_cells(
    document: CollectedDocument,
    page: CompiledMarimoPage,
) -> None:
    expected = [index for index, _ in enumerate(document.cells)]
    actual = [cell.index for cell in page.cells]
    if actual != expected:
        raise RuntimeError(
            f"marimo compiler returned cell indices {actual}; expected {expected}"
        )


def anywidget_node(
    cell: CompiledMarimoCell,
    payload: JsonObject,
    position: dict[str, Any] | None,
    assets: ProjectedAssets,
) -> dict[str, Any]:
    app = payload.get("app")
    app_id = (
        str(app["id"])
        if isinstance(app, dict) and isinstance(app.get("id"), str)
        else str(payload.get("appId") or "")
    )
    digest = hashlib.sha256(
        f"{app_id}\0{cell.index}\0{cell.html}".encode("utf-8")
    ).hexdigest()[:12]
    return {
        "type": "anywidget",
        "id": f"jupyter-book-marimo-{cell.index}-{digest}",
        "esm": assets.esm,
        "css": assets.css,
        "model": {"payload": payload},
        "position": position,
    }


def stage_assets(*, root: Path | None = None) -> ProjectedAssets:
    target_dir = (root or Path.cwd()) / GENERATED_DIR
    target_dir.mkdir(exist_ok=True)
    copy_package_asset(WIDGET_ESM, target_dir / WIDGET_ESM)
    copy_package_asset(BRIDGE_CSS, target_dir / BRIDGE_CSS)
    return ProjectedAssets(
        esm=asset_url(WIDGET_ESM),
        css=asset_url(BRIDGE_CSS),
    )


def copy_package_asset(name: str, target: Path) -> None:
    source = files("jupyter_book_marimo.assets").joinpath(name)
    with source.open("rb") as source_file:
        content = source_file.read()
    if target.exists() and target.read_bytes() == content:
        return
    with target.open("wb") as target_file:
        target_file.write(content)


def asset_url(name: str) -> str:
    return f"/{GENERATED_DIR}/{name}"
