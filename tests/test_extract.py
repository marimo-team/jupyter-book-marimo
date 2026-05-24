from __future__ import annotations

import asyncio
import warnings

import pytest
from jupyter_book_marimo import extract


def test_marimo_version_is_a_floor() -> None:
    assert extract.MIN_MARIMO_VERSION == "0.23.5"
    assert extract.version_tuple("0.23.6") > extract.version_tuple(
        extract.MIN_MARIMO_VERSION
    )


def test_output_model_omits_empty_runtime_fields() -> None:
    assert extract.output_model("<p>ok</p>") == {"html": "<p>ok</p>"}


def test_output_model_includes_page_runtime_fields() -> None:
    assert extract.output_model(
        "<marimo-island></marimo-island>",
        app_id="jb-test",
        notebook_code="app code",
        molab_notebook_code="molab app code",
        assets={"moduleScripts": ["/runtime.js"], "links": []},
        suppress_mimetypes={"application/vnd.marimo+error"},
    ) == {
        "html": "<marimo-island></marimo-island>",
        "appId": "jb-test",
        "notebookCode": "app code",
        "molabNotebookCode": "molab app code",
        "assets": {"moduleScripts": ["/runtime.js"], "links": []},
        "suppressMimetypes": ["application/vnd.marimo+error"],
    }


def test_widget_config_from_metadata_emits_molab_settings() -> None:
    assert extract.widget_config_from_metadata({}) == {"molab": {"enabled": True}}
    assert extract.widget_config_from_metadata({"molab": False}) == {
        "molab": {"enabled": False}
    }
    assert extract.widget_config_from_metadata({"molab": True}) == {
        "molab": {"enabled": True}
    }


def test_extract_attaches_widget_config_to_python_output_models() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {"eval": False, "molab": False},
                "cells": [{"code": "x = 1"}],
            }
        )
    )

    assert result["outputs"] == [
        {"html": "", "widgetConfig": {"molab": {"enabled": False}}}
    ]


def cell_plan(
    code: str,
    *,
    options: dict[str, object] | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> extract.CellPlan:
    payload: dict[str, object] = {
        "code": code,
        "options": {"language": "python", **(options or {})},
    }
    if start_line is not None:
        payload["startLine"] = start_line
    if end_line is not None:
        payload["endLine"] = end_line
    return extract.CellPlan.from_payload(0, payload, {})


def test_suppress_mime_renderers_removes_selected_marimo_mime_output() -> None:
    html = (
        "<marimo-cell-output>"
        "<marimo-mime-renderer "
        "data-mime='&quot;application/vnd.marimo+error&quot;' "
        "data-data='[]'></marimo-mime-renderer>"
        "<marimo-mime-renderer "
        "data-mime='&quot;text/plain&quot;' "
        "data-data='&quot;ok&quot;'></marimo-mime-renderer>"
        "</marimo-cell-output>"
    )

    filtered = extract.suppress_mime_renderers(
        html,
        {"application/vnd.marimo+error"},
    )

    assert "application/vnd.marimo+error" not in filtered
    assert "text/plain" in filtered


def test_suppress_mime_renderers_matches_data_mime_not_payload_text() -> None:
    html = (
        "<marimo-cell-output>"
        "<marimo-mime-renderer "
        "data-mime='&quot;text/plain&quot;' "
        "data-data='&quot;application/vnd.marimo+error&quot;'>"
        "</marimo-mime-renderer>"
        "</marimo-cell-output>"
    )

    filtered = extract.suppress_mime_renderers(
        html,
        {"application/vnd.marimo+error"},
    )

    assert "text/plain" in filtered
    assert "application/vnd.marimo+error" in filtered


def test_source_for_plain_python_cell_is_passthrough() -> None:
    assert extract.source_for_cell({"code": "x = 1"}) == "x = 1"


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

    sources = extract.molab_source_cells_from_page_source(
        source,
        [cell_plan("x = 1", start_line=15, end_line=17)],
        [extract.LineRange(9, 13)],
    )
    joined = "\n\n".join(sources)

    assert len(sources) == 3
    assert "title: Demo" not in joined
    assert "marimo-config" not in joined
    assert "Intro **markdown** before the first cell." in sources[0]
    assert "import marimo as _mo" in sources[0]
    assert sources[1] == "x = 1"
    assert "Markdown after the cell." in sources[2]


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

    sources = extract.molab_source_cells_from_page_source(
        source,
        [cell_plan("value = 41", start_line=21, end_line=23)],
        [extract.LineRange(13, 17)],
    )
    joined = "\n\n".join(sources)

    assert "not_executed = True" in joined
    assert "marimo-config" not in joined
    assert sources.count("value = 41") == 1
    assert "Intro before the executable cell." in joined
    assert "Markdown after the cell." in joined


def test_molab_source_cells_preserve_non_executed_cells_as_markdown() -> None:
    sources = extract.molab_source_cells_from_page_source(
        "",
        [cell_plan("print('broken'", options={"unparsable": True, "echo": True})],
    )

    assert len(sources) == 1
    assert "import marimo as _mo" in sources[0]
    assert "```python\\nprint('broken'\\n```" in sources[0]


def test_molab_source_cells_fall_back_to_planned_cells_without_source_ranges() -> None:
    sources = extract.molab_source_cells_from_page_source(
        "# Page markdown that cannot be safely aligned\n",
        [cell_plan("value = 41")],
    )

    assert sources == ["value = 41"]


def test_source_for_sql_cell_uses_inferred_language() -> None:
    source = extract.source_for_cell(
        {
            "code": "select * from numbers",
            "options": {"language": "sql", "query": "numbers"},
        }
    )

    assert "mo.sql" in source
    assert "select * from numbers" in source


def test_source_for_sql_cell_falls_back_on_invalid_query_target() -> None:
    source = extract.source_for_cell(
        {
            "code": "select * from numbers",
            "options": {"language": "sql", "query": "not-valid"},
        }
    )

    assert "_df = mo.sql" in source
    assert "not-valid = mo.sql" not in source


def test_source_for_sql_cell_falls_back_on_keyword_query_target() -> None:
    source = extract.source_for_cell(
        {
            "code": "select * from numbers",
            "options": {"language": "sql", "query": "class"},
        }
    )

    assert "_df = mo.sql" in source
    assert "class = mo.sql" not in source


def test_sql_code_to_python_matches_quarto_marimo_query_target_semantics() -> None:
    source = extract.sql_code_to_python(
        "SELECT * FROM df;",
        "filtered",
        hide_output=True,
        engine="engine",
    )

    assert "filtered = mo.sql(" in source
    assert "output=False" in source
    assert "engine=engine" in source


def test_disabled_sql_fallback_displays_original_source() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {},
                "cells": [
                    {
                        "code": "select * from numbers",
                        "options": {
                            "language": "sql",
                            "disabled": True,
                            "echo": True,
                        },
                    }
                ],
            }
        )
    )

    html = result["outputs"][0]["html"]
    assert "select * from numbers" in html
    assert "language-sql" in html
    assert "mo.sql" not in html


def test_page_eval_false_skips_execution_and_honors_echo() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {"eval": False, "echo": True},
                "cells": [
                    {
                        "code": 'raise RuntimeError("should not run")',
                        "options": {"language": "python"},
                    }
                ],
            }
        )
    )

    html = result["outputs"][0]["html"]
    assert "raise RuntimeError(&quot;should not run&quot;)" in html
    assert "could not compile" not in html


def test_cell_eval_false_skips_execution() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {},
                "cells": [
                    {
                        "code": 'raise RuntimeError("should not run")',
                        "options": {"language": "python", "eval": False, "echo": True},
                    }
                ],
            }
        )
    )

    assert (
        "raise RuntimeError(&quot;should not run&quot;)" in result["outputs"][0]["html"]
    )


def test_include_false_renders_intentionally_empty_output() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {},
                "cells": [
                    {
                        "code": "x = 1",
                        "options": {"language": "python", "include": False},
                    }
                ],
            }
        )
    )

    assert result["outputs"] == [
        {"html": "", "widgetConfig": {"molab": {"enabled": True}}}
    ]


def test_include_false_still_executes_for_later_cells() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "metadata": {},
                    "cells": [
                        {
                            "startLine": 1,
                            "code": "hidden_value = 41",
                            "options": {"include": False},
                        },
                        {
                            "startLine": 5,
                            "code": "hidden_value + 1",
                        },
                    ],
                }
            )
        )

    assert result["outputs"][0] == {
        "html": "",
        "widgetConfig": {"molab": {"enabled": True}},
    }
    assert "42" in result["outputs"][1]["html"]
    assert 'data-cell-idx="1"' in result["outputs"][1]["html"]


def test_error_false_fails_the_build_on_execution_error() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        with pytest.raises(RuntimeError, match=r"docs/tutorials/test.md:2"):
            asyncio.run(
                extract.extract(
                    {
                        "file": "docs/tutorials/test.md",
                        "metadata": {"error": False},
                        "cells": [
                            {"startLine": 2, "code": "planet = 'Mars'\nplanet"},
                            {"startLine": 7, "code": "planet = 'Earth'\nplanet"},
                        ],
                    }
                )
            )


def test_page_hide_output_suppresses_all_outputs_by_default() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "metadata": {"hide_output": True},
                    "cells": [
                        {"code": "1 + 1"},
                    ],
                }
            )
        )

    assert "data-mime" not in result["outputs"][0]["html"]


def test_as_bool_defaults_missing_values() -> None:
    assert extract.as_bool(None, True) is True
    assert extract.as_bool(None) is False


def test_pyproject_to_script_metadata_wraps_toml() -> None:
    assert (
        extract.pyproject_to_script_metadata('dependencies = ["marimo>=0.23.5"]')
        == '# /// script\n# dependencies = ["marimo>=0.23.5"]\n# ///\n'
    )


def test_page_cell_prefix_is_stable_and_page_specific() -> None:
    assert extract.page_cell_prefix(
        "docs/tutorials/intro.md"
    ) == extract.page_cell_prefix("docs/tutorials/intro.md")
    assert extract.page_cell_prefix(
        "docs/tutorials/intro.md"
    ) != extract.page_cell_prefix("docs/tutorials/dataflow.md")


def test_reactive_islands_use_browser_cell_indexes() -> None:
    island = (
        '<marimo-island data-app-id="jb-test" '
        'data-cell-id="server-cell" data-reactive="true"></marimo-island>'
    )

    rewritten = extract.use_browser_cell_index(island, 3)

    assert 'data-cell-id="server-cell"' not in rewritten
    assert 'data-cell-idx="3"' in rewritten


def test_browser_notebook_uses_page_cell_prefix() -> None:
    notebook_code = "\n".join(
        [
            "import marimo",
            "",
            "app = marimo.App()",
            "",
            "@app.cell",
            "def _():",
            "    return",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert "from marimo._ast.cell_manager import CellManager" in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_handles_formatted_app_constructor() -> None:
    notebook_code = "\n".join(
        [
            "import marimo as mo",
            "import marimo",
            "",
            'app = marimo.App(width="full")',
            "",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert 'app = marimo.App(width="full")' in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_handles_alias_only_app_constructor() -> None:
    notebook_code = "\n".join(
        [
            "import marimo as mo",
            "",
            "app = mo.App()",
            "",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert "from marimo._ast.cell_manager import CellManager" in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_handles_multiline_app_constructor() -> None:
    notebook_code = "\n".join(
        [
            "import marimo",
            "",
            "app = marimo.App(",
            '    width="full",',
            ")",
            "",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert '    width="full",' in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_reports_missing_app_constructor() -> None:
    try:
        extract.install_browser_cell_prefix("import marimo\n", "jbpage")
    except ValueError as exc:
        assert "cell prefix" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_extract_emits_runtime_fields_once_for_executable_cells() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "metadata": {},
                    "cells": [
                        {"code": "x = 1"},
                        {"code": "x"},
                    ],
                }
            )
        )

    assert result["outputs"][0]["appId"] == result["outputs"][1]["appId"]
    assert (
        f'CellManager(prefix="{extract.page_cell_prefix("docs/tutorials/test.md")}")'
        in result["outputs"][0]["notebookCode"]
    )
    assert "CellManager(prefix=" not in result["outputs"][0]["molabNotebookCode"]
    assert result["outputs"][0]["assets"]["moduleScripts"]
    assert "notebookCode" not in result["outputs"][1]
    assert "assets" not in result["outputs"][1]
    for output in result["outputs"]:
        assert "data-cell-idx" in output["html"]
        assert 'data-cell-id="' not in output["html"]


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

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "identity": "docs/tutorials/test.md",
                    "source": page_source,
                    "sourceRanges": {"config": [{"startLine": 9, "endLine": 13}]},
                    "metadata": {},
                    "cells": [{"code": "value = 41", "startLine": 15, "endLine": 17}],
                }
            )
        )

    output = result["outputs"][0]
    molab_code = output["molabNotebookCode"]

    assert "notebookCode" in output
    assert "This prose should open in Molab too." not in output["notebookCode"]
    assert "This prose should open in Molab too." in molab_code
    assert "More markdown after the executable cell." in molab_code
    assert "value = 41" in molab_code
    assert "marimo-config" not in molab_code


def test_extract_attaches_molab_notebook_code_without_page_source() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "identity": "docs/tutorials/test.md",
                    "metadata": {},
                    "cells": [{"code": "value = 41"}],
                }
            )
        )

    output = result["outputs"][0]

    assert "molabNotebookCode" in output
    assert "value = 41" in output["molabNotebookCode"]
