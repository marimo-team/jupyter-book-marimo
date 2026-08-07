from __future__ import annotations

from jupyter_book_marimo.protocol import (
    CompiledMarimoCell,
    CompiledMarimoOutput,
    CompiledMarimoPage,
    MarimoCellRequest,
    MarimoPageMetadata,
    MarimoPageRequest,
    MarimoPageRuntime,
)


def request(
    *cells: MarimoCellRequest,
    identity: str = "test:page",
    pyproject: str = "",
) -> MarimoPageRequest:
    return MarimoPageRequest(
        identity=identity,
        filename="page.md",
        metadata=MarimoPageMetadata(pyproject=pyproject),
        cells=tuple(cells),
    )


def cell(
    index: int,
    source: str = "x = 1",
    options: dict[str, object] | None = None,
) -> MarimoCellRequest:
    return MarimoCellRequest(
        index=index,
        source=source,
        options={"language": "python", **(options or {})},
    )


def compiled_cell(
    index: int,
    *,
    html: str = "<p>output</p>",
    include: bool = True,
) -> CompiledMarimoCell:
    return CompiledMarimoCell(
        index=index,
        html=html,
        options={
            "language": "python",
            "render": {
                "source": False,
                "output": True,
                "include": include,
                "editor": False,
                "error": True,
                "serverOutput": True,
            },
            "execution": {"enabled": True},
            "marimo": {"disabled": False, "unparsable": False},
        },
        output=CompiledMarimoOutput(
            mimetype="text/plain",
            data="output",
            html="<p>output</p>",
        ),
    )


def compiled_page(*cells: CompiledMarimoCell) -> CompiledMarimoPage:
    return CompiledMarimoPage(
        app=MarimoPageRuntime(
            id="marimo-test",
            runtime_cell_count=len(cells),
            assets={"moduleScripts": [], "links": []},
            notebook_code="import marimo as mo",
        ),
        cells=tuple(cells),
    )
