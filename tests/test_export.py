from __future__ import annotations

from pathlib import Path

from jupyter_book_marimo import export


def test_myst_config_extracts_pep_723_metadata_from_header() -> None:
    config = export.myst_config(
        {
            "header": "\n".join(
                [
                    "import marimo as mo",
                    "# /// script",
                    '# dependencies = ["polars"]',
                    "# ///",
                ]
            )
        }
    )

    assert config == "\n".join(
        [
            "```{marimo-config}",
            "---",
            "header: |-",
            "  import marimo as mo",
            "pyproject: |-",
            '  dependencies = ["polars"]',
            "---",
            "```",
            "",
            "",
        ]
    )


def test_myst_frontmatter_drops_marimo_runtime_metadata() -> None:
    assert export.myst_frontmatter(
        {
            "title": "Notebook",
            "marimo-version": "0.23.6",
            "width": "full",
            "header": "import marimo as mo",
        }
    ) == "\n".join(
        [
            "---",
            "title: Notebook",
            "---",
            "",
            "",
        ]
    )


def test_rewrite_marimo_fences_preserves_nested_literal_examples() -> None:
    rewritten = export.rewrite_marimo_fences(
        "\n".join(
            [
                "````markdown",
                "```python {.marimo}",
                "x = 1",
                "```",
                "````",
                "",
                '```python {.marimo hide_code="true" unparsable="true"}',
                "y = 2",
                "```",
            ]
        )
    )

    assert "```python {.marimo}" in rewritten
    assert "```{marimo} python" in rewritten
    assert ":hide-code: true" in rewritten
    assert ":unparseable: true" in rewritten


def test_rewrite_empty_python_cell_has_noop_body() -> None:
    assert export.rewrite_marimo_fences("```python {.marimo}\n```") == "\n".join(
        [
            "```{marimo} python",
            "pass",
            "```",
        ]
    )


def test_export_myst_combines_frontmatter_config_and_cells(
    tmp_path: Path, monkeypatch
) -> None:
    notebook = tmp_path / "lesson.py"
    notebook.write_text("unused", encoding="utf-8")
    monkeypatch.setattr(
        export,
        "notebook_to_marimo_markdown",
        lambda _path: "\n".join(
            [
                "---",
                "title: Lesson",
                "header: import marimo as mo",
                "---",
                "```python {.marimo}",
                "x = 1",
                "```",
            ]
        ),
    )

    assert export.export_myst(notebook) == "\n".join(
        [
            "---",
            "title: Lesson",
            "---",
            "",
            "```{marimo-config}",
            "---",
            "header: |-",
            "  import marimo as mo",
            "---",
            "```",
            "",
            "```{marimo} python",
            "x = 1",
            "```",
            "",
        ]
    )
