from __future__ import annotations

import hashlib
import json
import subprocess
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


def widget_source_text() -> str:
    return "\n".join(
        path.read_text() for path in sorted(WIDGET_SOURCE_DIR.glob("*.ts"))
    )


def marimo_node(
    value: str = "x = 1",
    options: dict[str, object] | None = None,
    line: int = 3,
) -> dict[str, object]:
    return {
        "type": "marimoCell",
        "language": "python",
        "value": value,
        "options": {"language": "python", **(options or {})},
        "position": {"start": {"line": line}},
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
                "pyproject": 'dependencies = ["marimo>=0.23.5"]',
            },
            "node": {"position": {"start": {"line": 1}}},
        },
    )

    assert node == {
        "type": "marimoConfig",
        "options": {
            "header": "import marimo as mo",
            "pyproject": 'dependencies = ["marimo>=0.23.5"]',
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
    source = widget_source_text()

    assert asset.exists()
    assert "widget/container-widget.ts" in bundle
    assert "export {" in bundle
    assert "const containerWidget" in source
    assert "Styling contract" in source
    assert "const globalThemeCss" in source
    assert ".${outputClass} :where(.myst-code)" in source
    assert "marimo-jupyter-book-pending" in bundle
    assert "marimo-table" in bundle
    assert "marimo-code-editor" in source
    assert "\npre,\npre code" not in source
    assert "\n.myst-code {" not in source
    assert "html.dark ." not in source
    assert "html.dark code:not(pre code)" not in source
    assert "Loading marimo output..." not in source


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
            "uv",
            "run",
            "deno",
            "bundle",
            "--quiet",
            "--platform",
            "browser",
            "--format",
            "esm",
            str(WIDGET_ENTRY),
            "-o",
            str(generated),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert generated.read_text() == WIDGET_BUNDLE.read_text()


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
