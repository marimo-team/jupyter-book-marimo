from __future__ import annotations

import asyncio

import pytest

from jupyter_book_marimo.compiler import (
    compile_page,
)
from jupyter_book_marimo.protocol import (
    CompiledMarimoPage,
    MarimoCellRequest,
    MarimoPageMetadata,
    MarimoPageRequest,
)

from helpers import cell, request


def test_compile_page_emits_protocol_runtime_and_static_output() -> None:
    page = compile_request(
        request(
            cell(0, "x = 41"),
            cell(1, "x + 1"),
            identity="test:reactive",
        )
    )

    assert page.app is not None
    assert page.app.id.startswith("marimo-")
    assert page.app.runtime_cell_count == 2
    assert len(page.app.assets["moduleScripts"]) >= 1
    assert "x = 41" in page.app.notebook_code
    assert page.app.runtime_payload["schemaVersion"] == 1
    assert page.app.runtime_payload["appId"] == page.app.id
    assert len(page.app.runtime_payload["cells"]) == 2
    assert [compiled.index for compiled in page.cells] == [0, 1]
    assert "42" in page.cells[1].html
    assert page.cells[1].output is not None
    assert page.cells[1].output.mimetype == "text/html"
    assert "42" in str(page.cells[1].output.data)
    assert "42" in page.cells[1].output.html


def test_compile_page_reports_cell_location_when_errors_are_hidden() -> None:
    failing = MarimoCellRequest(
        index=0,
        source="raise RuntimeError('boom')",
        options={"language": "python", "render": {"error": False}},
        start_line=17,
    )

    with pytest.raises(RuntimeError, match="page.md:17"):
        compile_request(request(failing))


def test_compiler_reports_effective_execution_and_unparsable_source() -> None:
    page = compile_request(
        request(
            cell(
                0,
                "disabled source",
                {"marimo": {"disabled": True}},
            ),
            cell(
                1,
                "unparsable source",
                {"marimo": {"unparsable": True}},
            ),
        )
    )

    assert page.cells[0].options["execution"]["enabled"] is False
    assert page.cells[1].options["execution"]["enabled"] is False
    assert page.cells[1].options["render"]["source"] is True
    assert "unparsable source" in page.cells[1].html


def test_compiler_uses_an_executable_setup_import() -> None:
    page_request = request(cell(0, "Hello", {"language": "markdown"}))
    page_request = MarimoPageRequest(
        identity=page_request.identity,
        filename=page_request.filename,
        metadata=MarimoPageMetadata(
            setup_cells=(
                MarimoCellRequest(
                    index=-1,
                    source="import marimo as mo",
                    options={
                        "language": "python",
                        "marimo": {"disabled": True},
                    },
                ),
            )
        ),
        cells=page_request.cells,
    )

    page = compile_request(page_request)

    assert page.cells[0].output is not None
    assert "Hello" in page.cells[0].output.html


def test_markdown_compiles_when_a_marimo_symbol_uses_the_mo_name() -> None:
    page_request = request(
        cell(0, "from marimo import md as mo"),
        cell(1, "Hello", {"language": "markdown"}),
    )

    page = compile_request(page_request)

    assert page.cells[1].output is not None
    assert "Hello" in page.cells[1].output.html


def compile_request(request: MarimoPageRequest) -> CompiledMarimoPage:
    return CompiledMarimoPage.from_json(asyncio.run(compile_page(request.to_json())))
