from __future__ import annotations

import pytest

from jupyter_book_marimo.authoring import (
    PageConfig,
    cell_from_directive,
    config_from_directive,
    pyproject_to_script_metadata,
)


def directive(
    language: str = "python",
    *,
    body: str = "x = 1",
    options: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "arg": language,
        "body": body,
        "options": options or {},
        "node": {
            "position": {
                "start": {"line": 4},
                "end": {"line": 8},
            }
        },
    }


def test_cell_directive_maps_authoring_options_to_page_protocol() -> None:
    cell = cell_from_directive(
        directive(
            "sql",
            body="select * from source",
            options={
                "query": "rows",
                "engine": "duckdb",
                "echo": False,
                "editor": True,
                "output": True,
                "server-output": False,
                "error": False,
                "include": True,
                "eval": False,
                "name": "query_cell",
                "column": 2,
            },
        )
    )

    assert cell.source == "select * from source"
    assert cell.options == {
        "language": "sql",
        "render": {
            "source": True,
            "editor": True,
            "output": True,
            "serverOutput": False,
            "error": False,
            "include": True,
        },
        "execution": {"enabled": False},
        "sql": {"outputName": "rows", "engine": "duckdb"},
        "name": "query_cell",
        "column": 2,
    }
    assert cell.request(3).to_json() == {
        "index": 3,
        "source": "select * from source",
        "options": cell.options,
        "startLine": 4,
        "endLine": 8,
    }


def test_hide_options_map_to_render_visibility() -> None:
    cell = cell_from_directive(
        directive(
            options={
                "echo": True,
                "editor": True,
                "output": True,
                "hide-code": True,
                "hide-output": True,
            }
        )
    )

    assert cell.options["render"] == {
        "source": False,
        "editor": False,
        "output": False,
    }


def test_unparsable_cells_render_source_and_disable_execution() -> None:
    cell = cell_from_directive(directive(options={"unparsable": True}))

    assert cell.options["marimo"] == {"unparsable": True}
    assert cell.options["execution"] == {"enabled": False}
    assert cell.options["render"]["source"] is True


def test_hide_code_hides_unparsable_source() -> None:
    cell = cell_from_directive(
        directive(options={"unparsable": True, "hide-code": True})
    )

    assert cell.options["render"]["source"] is False


def test_disabled_cells_report_execution_as_disabled() -> None:
    cell = cell_from_directive(directive(options={"disabled": True}))

    assert cell.options["execution"] == {"enabled": False}


def test_sql_options_are_omitted_from_python_cells() -> None:
    cell = cell_from_directive(directive("python", options={"query": "rows"}))

    assert "sql" not in cell.options


def test_directive_rejects_unknown_options() -> None:
    with pytest.raises(ValueError, match="Unsupported marimo option"):
        cell_from_directive(directive(options={"hide_code": True}))


def test_config_directive_maps_page_defaults_and_environment() -> None:
    config = config_from_directive(
        {
            "options": {
                "echo": True,
                "output": False,
                "eval": False,
                "header": "import polars as pl",
                "external-env": True,
            }
        }
    )

    assert config == PageConfig(
        defaults={
            "render": {"source": True, "output": False},
            "execution": {"enabled": False},
        },
        header="import polars as pl",
        external_env=True,
    )


def test_config_uses_directive_body_as_pyproject() -> None:
    config = config_from_directive(
        {
            "options": {"pyproject": ""},
            "body": 'requires-python = ">=3.12"\ndependencies = ["polars"]\n',
        }
    )

    assert config.pyproject == (
        'requires-python = ">=3.12"\ndependencies = ["polars"]\n'
    )


def test_config_rejects_two_environment_sources() -> None:
    with pytest.raises(ValueError, match="external-env and pyproject"):
        config_from_directive(
            {
                "options": {
                    "external-env": True,
                    "pyproject": 'dependencies = ["polars"]',
                }
            }
        )


def test_pyproject_becomes_pep_723_script_metadata() -> None:
    assert pyproject_to_script_metadata('dependencies = ["polars"]') == (
        '# /// script\n# dependencies = ["polars"]\n# ///\n'
    )
