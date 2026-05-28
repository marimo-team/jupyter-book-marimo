from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from jupyter_book_marimo.plugin import (
    directive_nodes,
    stylesheets_from_env,
    transform_document,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WIDGET_BUNDLE = REPO_ROOT / "src/jupyter_book_marimo/assets/container-widget.mjs"


def plugin_spec_from_command(command: list[str]) -> dict[str, object]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    spec = json.loads(result.stdout)
    assert isinstance(spec, dict)
    return spec


def directives_by_name(spec: dict[str, object]) -> dict[str, dict[str, object]]:
    directives = spec["directives"]
    assert isinstance(directives, list)
    return {directive["name"]: directive for directive in directives}


def assert_typed_options(directive: dict[str, object]) -> None:
    options = directive["options"]
    assert isinstance(options, dict)
    assert options
    for spec in options.values():
        assert isinstance(spec, dict)
        assert spec["type"] in {"boolean", "number", "string"}


def assert_plugin_spec_contract(spec: dict[str, object]) -> None:
    directives = directives_by_name(spec)
    assert set(directives) == {"marimo", "marimo-config"}
    assert_typed_options(directives["marimo"])
    assert_typed_options(directives["marimo-config"])
    transforms = spec["transforms"]
    assert isinstance(transforms, list)
    assert len(transforms) == 1
    transform = transforms[0]
    assert transform["name"] == "marimo-islands"
    assert transform["stage"] == "document"
    assert isinstance(transform["doc"], str)
    assert transform["doc"]


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


def transformed_payload(tree: dict[str, object]) -> dict[str, object]:
    payloads: list[dict[str, object]] = []
    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.side_effect = lambda payload: (
            payloads.append(payload)
            or {"outputs": [{"html": "<marimo-island></marimo-island>"}]}
        )
        transform_document(tree)
    return payloads[0]


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
                "pyproject": 'dependencies = ["pandas"]',
            },
            "node": {"position": {"start": {"line": 1}}},
        },
    )

    assert node == {
        "type": "marimoConfig",
        "options": {
            "header": "import marimo as mo",
            "molab": False,
            "pyproject": 'dependencies = ["pandas"]',
        },
        "position": {"start": {"line": 1}},
    }


def test_transform_replaces_marimo_nodes_and_consumes_config() -> None:
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
    assert result["children"][0]["model"]["html"] == "<marimo-island></marimo-island>"
    assert run_extractor.call_args.args[0]["metadata"] == {
        "header": "import marimo as mo"
    }
    assert run_extractor.call_args.args[0]["sourceRanges"] == {
        "config": [{"startLine": 1, "endLine": 3}]
    }
    assert run_extractor.call_args.args[0]["cells"][0]["code"] == "x = 1"


def test_transform_leaves_regular_code_fences_untouched() -> None:
    code_node = {
        "type": "code",
        "lang": "python",
        "meta": "{.marimo}",
        "value": "x = 1",
    }
    tree = {
        "type": "root",
        "children": [code_node],
    }

    result = transform_document(tree)

    assert result["children"][0] == code_node


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
    assert "customStylesheets" not in result["children"][0]["model"]
    [style_block] = result["children"][0]["model"]["customStyleBlocks"]
    assert style_block["id"]
    assert style_block["css"] == content


def test_transform_keeps_root_relative_custom_stylesheet_href() -> None:
    tree = {"type": "root", "children": [marimo_node("x = 1")]}
    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(tree, stylesheets=("/assets/marimo.css",))

    model = result["children"][0]["model"]
    assert model["customStylesheets"] == ["/assets/marimo.css"]
    assert "customStyleBlocks" not in model


def test_transform_embeds_absolute_custom_stylesheet_path(tmp_path: Path) -> None:
    stylesheet = tmp_path / "theme.css"
    stylesheet.write_text(".marimo { color: red; }\n", encoding="utf-8")
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(tree, stylesheets=(str(stylesheet),))

    model = result["children"][0]["model"]
    assert "customStylesheets" not in model
    [style_block] = model["customStyleBlocks"]
    assert style_block["id"]
    assert style_block["css"] == stylesheet.read_text(encoding="utf-8")


def test_transform_embeds_file_url_custom_stylesheet(tmp_path: Path) -> None:
    stylesheet = tmp_path / "theme.css"
    stylesheet.write_text(".marimo { color: red; }\n", encoding="utf-8")
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(tree, stylesheets=(stylesheet.as_uri(),))

    model = result["children"][0]["model"]
    assert "customStylesheets" not in model
    [style_block] = model["customStyleBlocks"]
    assert style_block["id"]
    assert style_block["css"] == stylesheet.read_text(encoding="utf-8")


def test_transform_payload_preserves_page_identity(tmp_path: Path, monkeypatch) -> None:
    page = tmp_path / "page.md"
    source = "# Page\n\n```{marimo} python\nx = 1\n```\n"
    page.write_text(source, encoding="utf-8")
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    payload = transformed_payload(tree)

    assert payload["file"] == str(page)
    assert payload["identity"] == "page.md"
    assert payload["source"] == source


def test_transform_payload_ignores_nogit_sources(tmp_path: Path, monkeypatch) -> None:
    page = tmp_path / "docs" / "page.md"
    private_page = tmp_path / "nogit" / "page.md"
    for path in (page, private_page):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "```{marimo} python\nx = 1\n```\n",
            encoding="utf-8",
        )
    tree = {"type": "root", "children": [marimo_node("x = 1")]}

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    payload = transformed_payload(tree)

    assert payload["file"] == str(page)
    assert payload["identity"] == "docs/page.md"


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


def test_transform_payload_uses_synthetic_identity_when_source_is_ambiguous(
    tmp_path: Path, monkeypatch
) -> None:
    for name in ("first.md", "second.md"):
        (tmp_path / name).write_text(
            "# Page\n\n```{marimo} python\nx = 1\n```\n",
            encoding="utf-8",
        )

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    tree = {"type": "root", "children": [marimo_node("x = 1")]}
    payload = transformed_payload(tree)
    repeated_payload = transformed_payload(
        {"type": "root", "children": [marimo_node("x = 1")]}
    )

    assert payload["file"] == payload["identity"]
    assert payload["source"] == ""
    assert Path(str(payload["identity"])).suffix == ".md"
    assert repeated_payload["identity"] == payload["identity"]


def test_stylesheets_from_env_accepts_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv(
        "JUPYTER_BOOK_MARIMO_STYLESHEETS",
        "styles/jupyter-book-marimo.css,https://example.com/marimo.css",
    )

    assert stylesheets_from_env() == (
        "styles/jupyter-book-marimo.css",
        "https://example.com/marimo.css",
    )


def test_stylesheets_from_env_accepts_json_list(monkeypatch) -> None:
    monkeypatch.setenv(
        "JUPYTER_BOOK_MARIMO_STYLESHEETS",
        '["styles/jupyter-book-marimo.css", "https://example.com/marimo.css"]',
    )

    assert stylesheets_from_env() == (
        "styles/jupyter-book-marimo.css",
        "https://example.com/marimo.css",
    )


def test_transform_writes_widget_asset_under_book_source_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    book = tmp_path / "docs"
    book.mkdir()
    (book / "myst.yml").write_text("project: {}\n", encoding="utf-8")
    page = book / "index.md"
    page.write_text("# Page\n\n```{marimo} python\nx = 1\n```\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BASE_URL", "/book/")

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = transform_document(
            {"type": "root", "children": [marimo_node("x = 1")]}
        )

    asset = book / ".jupyter-book-marimo" / "container-widget.mjs"

    assert result["children"][0]["esm"] == "/.jupyter-book-marimo/container-widget.mjs"
    assert asset.exists()
    assert asset.read_text() == WIDGET_BUNDLE.read_text()
    assert not (tmp_path / ".jupyter-book-marimo" / "container-widget.mjs").exists()


def test_container_widget_bundle_exports_anywidget_render() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "deno",
            "eval",
            (
                f"const mod = await import({json.dumps(WIDGET_BUNDLE.as_uri())});"
                "if (typeof mod.default?.render !== 'function') {"
                "throw new Error('missing anywidget render export');"
                "}"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_source_tree_console_script_emits_plugin_spec() -> None:
    spec = plugin_spec_from_command(["uv", "run", "jupyter-book-marimo"])

    assert_plugin_spec_contract(spec)


def test_source_tree_package_root_exposes_version() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from importlib.metadata import version; "
                "import jupyter_book_marimo as jbm; "
                "expected = version('jupyter-book-marimo'); "
                "raise SystemExit(0 if jbm.__version__ == expected else 1)"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_source_tree_package_main_emits_plugin_spec() -> None:
    spec = plugin_spec_from_command([sys.executable, "-m", "jupyter_book_marimo"])

    assert_plugin_spec_contract(spec)
