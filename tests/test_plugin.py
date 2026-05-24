from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from jupyter_book_marimo.plugin import (
    CONTAINER_WIDGET,
    STYLESHEETS_ENV,
    directive_nodes,
    source_path_for_cells,
    stylesheets_from_env,
    transform_document,
    widget_esm,
)

from jupyter_book_marimo.authoring import Cell

REPO_ROOT = Path(__file__).resolve().parents[1]
WIDGET_SOURCE_DIR = REPO_ROOT / "widget"
WIDGET_ENTRY = WIDGET_SOURCE_DIR / "container-widget.ts"
WIDGET_BUNDLE = REPO_ROOT / "src/jupyter_book_marimo/assets/container-widget.mjs"
WIDGET_BUNDLE_SCRIPT = REPO_ROOT / "scripts" / "bundle_widget.py"

_bundle_widget_spec = importlib.util.spec_from_file_location(
    "bundle_widget",
    WIDGET_BUNDLE_SCRIPT,
)
assert _bundle_widget_spec is not None
_bundle_widget = importlib.util.module_from_spec(_bundle_widget_spec)
assert _bundle_widget_spec.loader is not None
_bundle_widget_spec.loader.exec_module(_bundle_widget)
normalize_bundle = _bundle_widget.normalize_bundle


def marimo_node(
    value: str = "x = 1",
    options: dict[str, object] | None = None,
    line: int = 3,
    end_line: int | None = None,
) -> dict[str, object]:
    position: dict[str, object] = {"start": {"line": line}}
    if end_line is not None:
        position["end"] = {"line": end_line}
    return {
        "type": "marimoCell",
        "language": "python",
        "value": value,
        "options": {"language": "python", **(options or {})},
        "position": position,
    }


def test_marimo_directive_returns_internal_cell_node() -> None:
    [node] = directive_nodes(
        "marimo",
        {
            "arg": "sql",
            "body": "select 1",
            "options": {"query": "rows"},
            "node": {"position": {"start": {"line": 5}}},
        },
    )

    assert node == {
        "type": "marimoCell",
        "language": "sql",
        "value": "select 1",
        "options": {"language": "sql", "query": "rows"},
        "position": {"start": {"line": 5}},
    }


def test_marimo_config_directive_returns_internal_config_node() -> None:
    [node] = directive_nodes(
        "marimo-config",
        {
            "options": {
                "header": "import marimo as mo",
                "molab": False,
                "pyproject": 'dependencies = ["marimo>=0.23.5,<0.24"]',
            },
            "node": {"position": {"start": {"line": 1}}},
        },
    )

    assert node == {
        "type": "marimoConfig",
        "options": {
            "header": "import marimo as mo",
            "molab": False,
            "pyproject": 'dependencies = ["marimo>=0.23.5,<0.24"]',
        },
        "position": {"start": {"line": 1}},
    }


def test_transform_replaces_marimo_nodes_and_removes_config() -> None:
    tree = {
        "type": "root",
        "children": [
            {
                "type": "marimoConfig",
                "options": {"header": "import marimo as mo"},
                "position": {"start": {"line": 1}, "end": {"line": 3}},
            },
            marimo_node("x = 1"),
        ],
    }

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(tree)

    assert len(result["children"]) == 1
    assert result["children"][0]["type"] == "anywidget"
    assert run_extractor.call_args.args[0]["metadata"] == {
        "header": "import marimo as mo"
    }
    assert run_extractor.call_args.args[0]["sourceRanges"] == {
        "config": [{"startLine": 1, "endLine": 3}]
    }
    assert run_extractor.call_args.args[0]["cells"][0]["code"] == "x = 1"


def test_transform_leaves_regular_code_fences_untouched() -> None:
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "meta": "{.marimo}",
                "value": "x = 1",
            },
        ],
    }

    result = transform_document(tree)

    assert result["children"][0]["type"] == "code"


def test_transform_rejects_multiple_config_nodes() -> None:
    tree = {
        "type": "root",
        "children": [
            {"type": "marimoConfig", "options": {"echo": True}},
            {"type": "marimoConfig", "options": {"output": False}},
        ],
    }

    with pytest.raises(ValueError, match="Only one marimo-config"):
        transform_document(tree)


def test_transform_rejects_multiple_empty_config_nodes() -> None:
    tree = {
        "type": "root",
        "children": [
            {"type": "marimoConfig", "options": {}},
            {"type": "marimoConfig", "options": {}},
        ],
    }

    with pytest.raises(ValueError, match="Only one marimo-config"):
        transform_document(tree)


def test_transform_fails_on_output_count_mismatch() -> None:
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {"outputs": []}
        with pytest.raises(RuntimeError, match="returned 0 outputs for 1 cells"):
            transform_document(tree)


def test_transform_attaches_custom_stylesheet_assets(
    tmp_path: Path, monkeypatch
) -> None:
    stylesheet = tmp_path / "styles" / "theme.css"
    stylesheet.parent.mkdir()
    stylesheet.write_text(".marimo-jupyter-book-output { --jbm-code-bg: white; }\n")
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    monkeypatch.chdir(tmp_path)
    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(
            tree,
            stylesheets=("styles/theme.css",),
        )

    content = stylesheet.read_text()
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    assert "customStylesheets" not in result["children"][0]["model"]
    assert result["children"][0]["model"]["customStyleBlocks"] == [
        {"id": f"theme-{digest}", "css": content}
    ]


def test_source_path_locator_preserves_page_identity(
    tmp_path: Path, monkeypatch
) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "# Page\n\n```{marimo} python\nx = 1\n```\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)

    assert source_path_for_cells([Cell("x = 1", {})]) == page


def test_transform_payload_includes_resolved_page_source(
    tmp_path: Path, monkeypatch
) -> None:
    page = tmp_path / "page.md"
    source = "# Page\n\nIntro markdown.\n\n```{marimo} python\nx = 1\n```\n"
    page.write_text(source, encoding="utf-8")
    tree = {"type": "root", "children": [marimo_node("x = 1", line=5, end_line=7)]}
    payloads: list[dict[str, object]] = []

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.side_effect = lambda payload: (
            payloads.append(payload)
            or {"outputs": [{"html": "<marimo-island></marimo-island>"}]}
        )
        transform_document(tree)

    assert payloads[0]["file"] == str(page)
    assert payloads[0]["identity"] == "page.md"
    assert payloads[0]["source"] == source
    assert payloads[0]["cells"][0]["startLine"] == 5
    assert payloads[0]["cells"][0]["endLine"] == 7
    assert payloads[0]["sourceRanges"] == {"config": []}


def test_source_path_locator_falls_back_when_source_is_ambiguous(
    tmp_path: Path, monkeypatch
) -> None:
    for name in ("first.md", "second.md"):
        (tmp_path / name).write_text(
            "# Page\n\n```{marimo} python\nx = 1\n```\n",
            encoding="utf-8",
        )

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)

    assert source_path_for_cells([Cell("x = 1", {})]) is None


def test_stylesheets_from_env_accepts_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv(
        STYLESHEETS_ENV,
        "styles/jupyter-book-marimo.css,https://example.com/marimo.css",
    )

    assert stylesheets_from_env() == (
        "styles/jupyter-book-marimo.css",
        "https://example.com/marimo.css",
    )


def test_stylesheets_from_env_accepts_json_list(monkeypatch) -> None:
    monkeypatch.setenv(
        STYLESHEETS_ENV,
        '["styles/jupyter-book-marimo.css", "https://example.com/marimo.css"]',
    )

    assert stylesheets_from_env() == (
        "styles/jupyter-book-marimo.css",
        "https://example.com/marimo.css",
    )


def test_widget_esm_stays_source_relative_with_base_url(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BASE_URL", "/book/")

    assert widget_esm() == f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"


def test_widget_esm_stays_source_relative_with_bare_base_url(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BASE_URL", "book")

    assert widget_esm() == f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"


def test_container_widget_asset_is_named_and_source_like(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert widget_esm() == f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"
    asset = tmp_path / ".jupyter-book-marimo" / CONTAINER_WIDGET
    bundle = asset.read_text()

    assert asset.exists()
    assert bundle == WIDGET_BUNDLE.read_text()
    assert bundle.startswith("// Generated by `make widget-build` from widget/.")
    assert "widget/container-widget.ts" in bundle
    assert "export {" in bundle


@pytest.mark.parametrize("target", [WIDGET_ENTRY, WIDGET_BUNDLE])
def test_container_widget_assets_are_deno_checkable(target: Path) -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "deno",
            "check",
            str(target),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_container_widget_bundle_is_current(tmp_path: Path) -> None:
    generated = tmp_path / CONTAINER_WIDGET
    result = subprocess.run(
        [
            sys.executable,
            str(WIDGET_BUNDLE_SCRIPT),
            str(generated),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert generated.read_text() == WIDGET_BUNDLE.read_text()


def test_widget_bundle_normalization_removes_local_deno_cache_paths() -> None:
    bundle = """
// ../../../../Library/Caches/deno/npm/registry.npmjs.org/lz-string/1.5.0/libs/lz-string.js
var require_lz_string = __commonJS({
  "../../../../Library/Caches/deno/npm/registry.npmjs.org/lz-string/1.5.0/libs/lz-string.js"(exports, module) {
  }
});
"""

    normalized = normalize_bundle(bundle)

    assert "Library/Caches/deno" not in normalized
    assert "// npm:lz-string@1.5.0/libs/lz-string.js" in normalized
    assert '"npm:lz-string@1.5.0/libs/lz-string.js"' in normalized


def test_plugin_spec_includes_directives() -> None:
    result = subprocess.run(
        ["uv", "run", "jupyter-book-marimo"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    spec = json.loads(result.stdout)
    assert [directive["name"] for directive in spec["directives"]] == [
        "marimo",
        "marimo-config",
    ]
    marimo_options = spec["directives"][0]["options"]
    config_options = spec["directives"][1]["options"]
    assert "warning" not in marimo_options
    assert "warning" not in config_options
    assert marimo_options["hide-code"]["type"] == "boolean"
    assert config_options["pyproject"]["type"] == "string"
