from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from jupyter_book_marimo.plugin import (
    CONTAINER_WIDGET,
    STYLESHEETS_ENV,
    SourceContext,
    parsed_source_pages,
    source_page_context,
    stylesheets_from_env,
    transform_document,
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
            context.return_value = SourceContext(
                {"header": "# Copyright 2026 Marimo. All rights reserved"},
                {},
                None,
            )
            run_extractor.return_value = {
                "outputs": [{"html": "<marimo-island></marimo-island>"}]
            }
            result = transform_document(tree)

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
    context = source_page_context(tree)

    assert context.metadata == {"pyproject": 'dependencies = ["marimo>=0.23.5"]'}
    assert context.path == tmp_path / "page.md"
    assert context.options_by_signature[(9, "python", "x = 1")] == {
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
        result = transform_document(tree)

    assert result["children"][0]["type"] == "comment"
    assert result["children"][1]["type"] == "anywidget"


def test_transform_attaches_custom_stylesheet_assets(
    tmp_path: Path, monkeypatch
) -> None:
    stylesheet = tmp_path / "styles" / "theme.css"
    stylesheet.parent.mkdir()
    stylesheet.write_text(".marimo-jupyter-book-output { --jbm-code-bg: white; }\n")
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "meta": "{.marimo}",
                "value": "x = 1",
                "position": {"start": {"line": 8}},
            },
        ],
    }

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
        context.return_value = SourceContext(
            {},
            {(3, "python", "x = 1"): {"language": "python", "hide_code": True}},
            None,
        )
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        transform_document(tree)

    assert run_extractor.call_args.args[0]["cells"][0]["options"]["hide_code"] is True


def test_source_page_context_scans_markdown_sources(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "page.md").write_text(
        '# Title\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n'
    )

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    context = source_page_context()

    assert context.options_by_signature[(3, "python", "x = 1")] == {
        "language": "python",
        "hide_code": True,
    }


def test_source_page_context_uses_current_tree_to_pick_page(
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
    context = source_page_context(tree)

    assert context.options_by_signature == {
        (3, "python", "y = 2"): {"language": "python", "editor": True}
    }


def test_parsed_source_pages_reads_markdown_as_utf8(
    tmp_path: Path, monkeypatch
) -> None:
    page = tmp_path / "page.md"
    page.write_text("# Café\n\n```python {.marimo}\nx = 1\n```\n", encoding="utf-8")
    read_encodings: list[str | None] = []
    original_read_text = Path.read_text

    def read_text(path: Path, *args, **kwargs):
        read_encodings.append(kwargs.get("encoding"))
        return original_read_text(path, *args, **kwargs)

    parsed_source_pages.cache_clear()
    monkeypatch.setattr(Path, "read_text", read_text)

    parsed_source_pages(tmp_path.resolve())

    assert read_encodings == ["utf-8"]


def test_source_page_context_reuses_source_pages(tmp_path: Path, monkeypatch) -> None:
    page = tmp_path / "page.md"
    page.write_text('# Title\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n')
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    parsed_source_pages.cache_clear()

    first_context = source_page_context(tree)
    page.write_text('# Title\n\n```python {.marimo editor="true"}\nx = 1\n```\n')
    second_context = source_page_context(tree)

    assert first_context.options_by_signature[(3, "python", "x = 1")] == {
        "language": "python",
        "hide_code": True,
    }
    assert second_context.options_by_signature[(3, "python", "x = 1")] == {
        "language": "python",
        "hide_code": True,
    }


def test_source_page_context_reports_ambiguous_source_pages(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "first.md").write_text(
        '# First\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n'
    )
    (tmp_path / "second.md").write_text(
        '# Second\n\n```python {.marimo editor="true"}\nx = 1\n```\n'
    )
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)

    with pytest.raises(ValueError, match="Ambiguous marimo source page"):
        source_page_context(tree)


def test_source_page_context_ignores_unrelated_invalid_frontmatter(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "page.md").write_text(
        '# Page\n\n```python {.marimo echo="true"}\nx = 1\n```\n'
    )
    (tmp_path / "draft.md").write_text(
        "---\noptions:\n  marimo: definitely-not-a-mapping\n---\n\n"
        "```python {.marimo}\ny = 2\n```\n"
    )
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)

    context = source_page_context(tree)

    assert context.path == tmp_path / "page.md"
    assert context.options_by_signature[(3, "python", "x = 1")] == {
        "language": "python",
        "echo": True,
    }


def test_source_page_context_matches_indented_source_fence(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "page.md").write_text(
        '# Page\n\n  ```python {.marimo echo="true"}\n  x = 1\n  ```\n'
    )
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)

    context = source_page_context(tree)

    assert context.path == tmp_path / "page.md"
    assert context.options_by_signature[(3, "python", "x = 1")] == {
        "language": "python",
        "echo": True,
    }


def test_transform_passes_matched_source_path_to_extractor(
    tmp_path: Path, monkeypatch
) -> None:
    page = tmp_path / "page.md"
    page.write_text("# Page\n\n```python {.marimo}\nx = 1\n```\n")
    tree = {
        "type": "root",
        "children": [
            {
                "type": "code",
                "lang": "python",
                "value": "x = 1",
                "position": {"start": {"line": 3}},
            }
        ],
    }

    monkeypatch.setattr("jupyter_book_marimo.plugin.Path.cwd", lambda: tmp_path)
    with patch("jupyter_book_marimo.plugin.run_extractor") as run_extractor:
        run_extractor.return_value = {
            "outputs": [{"html": "<marimo-island></marimo-island>"}]
        }
        transform_document(tree)

    assert run_extractor.call_args.args[0]["file"] == str(page)
    assert run_extractor.call_args.args[0]["identity"] == "page.md"


def test_container_widget_asset_is_named_and_source_like(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert widget_esm() == f"/.jupyter-book-marimo/{CONTAINER_WIDGET}"
    asset = tmp_path / ".jupyter-book-marimo" / CONTAINER_WIDGET
    source = asset.read_text()

    assert asset.exists()
    assert "const containerWidget" in source
    assert "Styling contract" in source
    assert "const globalThemeCss" in source
    assert ".${outputClass} :where(.myst-code)" in source
    assert "marimo-jupyter-book-pending" in source
    assert "marimo-table" in source
    assert "marimo-code-editor" in source
    assert "\npre,\npre code" not in source
    assert "\n.myst-code {" not in source
    assert "html.dark ." not in source
    assert "html.dark code:not(pre code)" not in source
    assert "Loading marimo output..." not in source
    assert "\nvar " not in source


def test_container_widget_asset_is_valid_javascript() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    result = subprocess.run(
        [node, "--check", "src/jupyter_book_marimo/assets/container-widget.mjs"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
