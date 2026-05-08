from __future__ import annotations

from jupyter_book_marimo.syntax import (
    code_cell_from_node,
    metadata_from_frontmatter,
    parse_code_meta,
    parse_plain_fence_info,
    read_frontmatter,
    source_page,
    source_fences,
)


def test_parse_code_meta_reads_fence_options() -> None:
    assert parse_code_meta("sql", '{.marimo query="rows" hide_output="True"}') == {
        "language": "sql",
        "query": "rows",
        "hide_output": True,
    }


def test_parse_code_meta_ignores_plain_python_fences() -> None:
    assert parse_code_meta("python", None) is None
    assert parse_code_meta("python", "{}") is None


def test_metadata_is_read_from_frontmatter_options_marimo_namespace() -> None:
    frontmatter = read_frontmatter(
        """---
title: Example
options:
  marimo:
    header: |
      import marimo as mo
    pyproject: |
      dependencies = ["marimo>=0.23.5"]
---

# Example
"""
    )

    assert metadata_from_frontmatter(frontmatter) == {
        "header": "import marimo as mo",
        "pyproject": 'dependencies = ["marimo>=0.23.5"]',
    }


def test_code_cell_from_node_reads_regular_code_fences() -> None:
    cell = code_cell_from_node(
        {
            "type": "code",
            "lang": "python",
            "meta": '{.marimo hide_code="true"}',
            "value": "x = 1",
            "position": {"start": {"line": 10}},
        }
    )

    assert cell is not None
    assert cell.payload()["startLine"] == 10
    assert cell.options["hide_code"] is True


def test_parse_plain_fence_info_reads_attributes_after_language() -> None:
    assert parse_plain_fence_info('python {.marimo hide_code="true"}') == {
        "language": "python",
        "hide_code": True,
    }


def test_source_fences_recovers_plain_marimo_fences_by_line() -> None:
    [fence] = source_fences(
        '# Title\n\n```python {.marimo hide_code="true"}\nx = 1\n```\n'
    )

    assert fence.start_line == 3
    assert fence.language == "python"
    assert fence.code == "x = 1"
    assert fence.options["hide_code"] is True


def test_source_page_reads_frontmatter_and_fences() -> None:
    page = source_page(
        """---
title: Example
options:
  marimo:
    header: |
      import marimo as mo
---

# Title

```python {.marimo}
x = 1
```
"""
    )

    assert page.metadata == {"header": "import marimo as mo"}
    assert page.fences[0].start_line == 11
    assert page.fences[0].options == {"language": "python"}
