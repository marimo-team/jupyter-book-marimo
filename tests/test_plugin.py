from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from jupyter_book_marimo.plugin import (
    CONTAINER_WIDGET,
    run_transform,
    source_fence_lookup,
    source_page_context,
    widget_esm,
)


def test_transform_replaces_marked_cells_and_reads_frontmatter_metadata() -> None:
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "meta": "{.marimo}",
                "value": "x = 1",
                "position": {"start": {"line": 9}},
            },
        ],
    }

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        with patch("jupyter_book_marimo.plugin.source_page_context") as context:
            context.return_value = (
                {"header": "# Copyright 2026 Marimo. All rights reserved"},
                {},
            )
            run_extractor.return_value = {
                "outputs": [{"html": "<marimo-island></marimo-island>"}]
            }
            result = run_transform("marimo-code-fences", tree)

    assert result["children"][0]["type"] == "anywidget"
    assert (
        run_extractor.call_args.args[0]["metadata"]["header"]
        == "# Copyright 2026 Marimo. All rights reserved"
    )
    assert run_extractor.call_args.args[0]["cells"][0]["code"] == "x = 1"


def test_source_page_context_matches_current_page_frontmatter(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "page.md").write_text(
        """---
title: Example
options:
  marimo:
    pyproject: |
      dependencies = ["marimo>=0.23.5"]
---

```python {.marimo hide_code="true"}
x = 1
```
"""
    )
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 9}},
            },
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    metadata, lookup = source_page_context(tree)

    assert metadata == {"pyproject": 'dependencies = ["marimo>=0.23.5"]'}
    assert lookup[(9, "python", "x = 1")] == {
        "language": "python",
        "hide_code": True,
    }


def test_transform_preserves_regular_comments() -> None:
    tree = {
        "type": "root",
        "children": [
            {"type": "comment", "value": "regular comment"},
            {
                "type": "code",
                "lang": "python",
                "meta": "{.marimo}",
                "value": "x = 1",
                "position": {"start": {"line": 8}},
            },
        ],
    }

    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        result = run_transform("marimo-code-fences", tree)

    assert result["children"][0]["type"] == "comment"
    assert result["children"][1]["type"] == "anywidget"


def test_transform_recovers_plain_fence_options_from_source_positions() -> None:
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            },
        ],
    }

    with (
        patch("jupyter_book_marimo.plugin.source_page_context") as context,
        patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor,
    ):
        context.return_value = (
            {},
            {(3, "python", "x = 1"): {"language": "python", "hide_code": True}},
        )
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        run_transform("marimo-code-fences", tree)

    assert run_extractor.call_args.args[0]["cells"][0]["options"]["hide_code"] is True


def test_source_fence_lookup_scans_markdown_sources(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "page.md").write_text(
        '# Title\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n'
    )

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    fixture = source_fence_lookup()

    assert fixture[(3, "python", "x = 1")] == {
        "language": "python",
        "hide_code": True,
    }


def test_source_fence_lookup_uses_current_tree_to_pick_page(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "first.md").write_text(
        '# First\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n'
    )
    (tmp_path / "second.md").write_text(
        '# Second\n\n```python {.marimo editor="true"}\ny = 2\n```\n'
    )
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "y = 2",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    fixture = source_fence_lookup(tree)

    assert fixture == {(3, "python", "y = 2"): {"language": "python", "editor": True}}


def test_public_docs_use_plain_language_fence_api() -> None:
    root = Path.cwd()
    public_markdown = [
        root / "README.md",
        root / "docs" / "index.md",
        *sorted((root / "docs" / "tutorials").glob("*.md")),
    ]
    old_style: list[str] = []
    for path in public_markdown:
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if line.startswith("```{") and ".marimo" in line:
                old_style.append(f"{path.relative_to(root)}:{line_number}:{line}")

    assert old_style == []


def test_public_docs_use_frontmatter_for_marimo_metadata() -> None:
    root = Path.cwd()
    public_markdown = [
        root / "README.md",
        root / "docs" / "index.md",
        *sorted((root / "docs" / "tutorials").glob("*.md")),
    ]
    old_style: list[str] = []
    legacy_tokens = ("marimo-" + "header", "marimo-" + "pyproject")
    for path in public_markdown:
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if any(token in line for token in legacy_tokens):
                old_style.append(f"{path.relative_to(root)}:{line_number}:{line}")

    assert old_style == []


def test_container_widget_asset_is_named_and_source_like(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert widget_esm() == f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"
    asset = tmp_path / ".jupyter-book-marimo" / CONTAINER_WIDGET
    source = asset.read_text()

    assert asset.exists()
    assert "const containerWidget" in source
    assert "const globalThemeCss" in source
    assert ".myst-code" in source
    assert ".${outputClass} pre" in source
    assert "\nvar " not in source
