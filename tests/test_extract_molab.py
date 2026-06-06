from __future__ import annotations

from textwrap import dedent

from jupyter_book_marimo.molab import (
    LineRange,
    molab_source_cells_from_page_source,
)
from extract_helpers import (
    assignment_values,
    cell_plan,
    markdown_cell_literals,
    run_extract,
)


def normalized_markdown_literals(source: str) -> list[str]:
    return [dedent(literal).strip() for literal in markdown_cell_literals(source)]


def test_molab_source_cells_interleave_page_markdown_and_directives() -> None:
    source = """---
title: Demo
---

# Demo page

Intro **markdown** before the first cell.

```{marimo-config}
---
eval: true
---
```

```{marimo} python
x = 1
```

Markdown after the cell.
"""

    sources = molab_source_cells_from_page_source(
        source,
        [cell_plan("x = 1", start_line=15, end_line=17)],
        [LineRange(9, 13)],
    )

    assert len(sources) == 3
    assert normalized_markdown_literals(sources[0]) == [
        "# Demo page\n\nIntro **markdown** before the first cell."
    ]
    assert sources[1] == "x = 1"
    assert normalized_markdown_literals(sources[2]) == ["Markdown after the cell."]


def test_molab_source_cells_strip_non_rendered_markdown_comments() -> None:
    source = """# Demo page

Visible intro.

<!-- hidden token -->
% hidden MyST comment

```{marimo} python
x = 1
```
"""

    sources = molab_source_cells_from_page_source(
        source,
        [cell_plan("x = 1", start_line=8, end_line=10)],
    )

    markdown_cells = [
        normalized
        for source in sources
        for normalized in normalized_markdown_literals(source)
    ]
    assert markdown_cells == ["# Demo page\n\nVisible intro."]


def test_molab_source_cells_preserve_comment_like_lines_in_fences() -> None:
    source = """# Demo page

```python
<!-- visible in code -->
%matplotlib inline
value = 1
```

```{marimo} python
x = 1
```
"""

    sources = molab_source_cells_from_page_source(
        source,
        [cell_plan("x = 1", start_line=9, end_line=11)],
    )

    assert normalized_markdown_literals(sources[0]) == [
        "# Demo page\n\n```python\n"
        "<!-- visible in code -->\n"
        "%matplotlib inline\n"
        "value = 1\n"
        "```"
    ]


def test_molab_source_cells_preserve_literal_marimo_fences_before_real_cell() -> None:
    source = """---
title: Demo
---

# Demo page

````markdown
```{marimo} python
not_executed = True
```
````

```{marimo-config}
---
eval: true
---
```

Intro before the executable cell.

```{marimo} python
value = 41
```

Markdown after the cell.
"""

    sources = molab_source_cells_from_page_source(
        source,
        [cell_plan("value = 41", start_line=21, end_line=23)],
        [LineRange(13, 17)],
    )

    assert len(sources) == 4
    assert normalized_markdown_literals(sources[0]) == [
        "# Demo page\n\n````markdown\n"
        "```{marimo} python\n"
        "not_executed = True\n"
        "```\n"
        "````"
    ]
    assert [
        source for source in sources if assignment_values(source, "value") == [41]
    ] == ["value = 41"]
    assert normalized_markdown_literals(sources[1]) == [
        "Intro before the executable cell."
    ]
    assert normalized_markdown_literals(sources[3]) == ["Markdown after the cell."]


def test_molab_source_cells_preserve_non_executed_cells_as_markdown() -> None:
    sources = molab_source_cells_from_page_source(
        "",
        [cell_plan("print('broken'", options={"unparsable": True, "echo": True})],
    )

    assert len(sources) == 1
    assert normalized_markdown_literals(sources[0]) == [
        "```python\nprint('broken'\n```"
    ]


def test_extract_reports_molab_fallback_when_source_ranges_are_missing() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "identity": "docs/tutorials/test.md",
            "source": "# Page markdown that cannot be safely aligned\n",
            "metadata": {},
            "cells": [{"code": "value = 41"}],
        }
    )

    output = result["outputs"][0]
    assert output["molabSourceFallbackReason"] == "missing_source_ranges"
    assert assignment_values(output["molabNotebookCode"], "value") == [41]


def test_extract_reports_molab_fallback_when_source_ranges_are_out_of_bounds() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "identity": "docs/tutorials/test.md",
            "source": "# Short page\n",
            "metadata": {},
            "cells": [{"code": "value = 41", "startLine": 10, "endLine": 12}],
        }
    )

    output = result["outputs"][0]
    assert output["molabSourceFallbackReason"] == "out_of_bounds_source_ranges"
    assert assignment_values(output["molabNotebookCode"], "value") == [41]


def test_extract_attaches_molab_notebook_code_with_page_markdown() -> None:
    page_source = """---
title: Demo
---

# Demo page

This prose should open in Molab too.

```{marimo-config}
---
eval: true
---
```

```{marimo} python
value = 41
```

More markdown after the executable cell.
"""

    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "identity": "docs/tutorials/test.md",
            "source": page_source,
            "sourceRanges": {"config": [{"startLine": 9, "endLine": 13}]},
            "metadata": {},
            "cells": [{"code": "value = 41", "startLine": 15, "endLine": 17}],
        }
    )

    output = result["outputs"][0]
    molab_code = output["molabNotebookCode"]

    assert "notebookCode" in output
    assert markdown_cell_literals(output["notebookCode"]) == []
    assert normalized_markdown_literals(molab_code) == [
        "# Demo page\n\nThis prose should open in Molab too.",
        "More markdown after the executable cell.",
    ]
    assert assignment_values(molab_code, "value") == [41]


def test_extract_attaches_molab_notebook_code_from_cell_source() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "identity": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [{"code": "value = 41"}],
        }
    )

    output = result["outputs"][0]

    assert "molabNotebookCode" in output
    assert assignment_values(output["molabNotebookCode"], "value") == [41]
    assert output["molabSourceFallbackReason"] == "empty_page_source"


def test_molab_false_omits_molab_notebook_payload() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "identity": "docs/tutorials/test.md",
            "metadata": {"molab": False},
            "cells": [{"code": "value = 41"}],
        }
    )

    output = result["outputs"][0]

    assert output["widgetConfig"] == {"molab": {"enabled": False}}
    assert "notebookCode" in output
    assert "molabNotebookCode" not in output
    assert "molabSourceFallbackReason" not in output
