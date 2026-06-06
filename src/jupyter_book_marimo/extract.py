#!/usr/bin/env python3
"""Execute a page and return anywidget models for its marimo cells.

The extractor resolves authoring options, runs marimo, rewrites cell identifiers for the
browser runtime, and attaches one shared hydration payload to the page outputs.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import Any, Protocol
import asyncio
import json
import sys

from .authoring import as_bool
from .cell_plan import CellPlan
from .header_cells import (
    add_header_cells,
    fail_on_header_errors,
    hidden_header_islands,
    runtime_header_sources,
)
from .island_output import (
    ERROR_MIMETYPES,
    has_error_mimetype,
    hidden_runtime_output,
    hide_island_output,
    output_model,
    suppress_mime_renderers,
    use_browser_cell_index,
    widget_config_from_metadata,
)
from .molab import (
    LineRange,
    MolabNotebookExport,
    build_molab_notebook_export,
)
from .runtime import Runtime, page_cell_prefix, page_digest


@dataclass(frozen=True)
class PendingCellOutput:
    plan: CellPlan
    stub: Any
    browser_cell_index: int


@dataclass(frozen=True)
class RuntimePayload:
    did_error: bool
    notebook_code: str = ""
    molab_notebook_code: str = ""
    molab_source_fallback_reason: str = ""
    assets: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionRequest:
    metadata: dict[str, Any]
    cells: list[dict[str, Any]]
    filename: str
    identity: str
    source: str
    config_ranges: list[LineRange]
    widget_config: dict[str, Any]
    app_id: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExtractionRequest:
        metadata = payload.get("metadata") or {}
        document_options = metadata if isinstance(metadata, dict) else {}
        filename = str(payload.get("file") or "")
        identity = str(payload.get("identity") or filename)
        return cls(
            metadata=document_options,
            cells=list(payload.get("cells") or []),
            filename=filename,
            identity=identity,
            source=str(payload.get("source") or ""),
            config_ranges=source_ranges_from_payload(payload),
            widget_config=widget_config_from_metadata(document_options),
            app_id="jb-" + page_digest(identity),
        )

    @property
    def header(self) -> str:
        return str(self.metadata.get("header") or "")

    @property
    def pyproject(self) -> str:
        return str(self.metadata.get("pyproject") or "")


class RuntimeFactory(Protocol):
    def __call__(self, app_id: str, cell_prefix: str) -> Runtime: ...


class MolabExporter(Protocol):
    def __call__(
        self,
        source: str,
        plans: Sequence[CellPlan],
        *,
        identity: str,
        config_ranges: list[LineRange] | None = None,
        pyproject: str = "",
        header: str = "",
    ) -> MolabNotebookExport: ...


def default_runtime_factory(app_id: str, cell_prefix: str) -> Runtime:
    return Runtime(app_id=app_id, cell_prefix=cell_prefix)


@dataclass(frozen=True)
class ExtractorDependencies:
    runtime_factory: RuntimeFactory = default_runtime_factory
    molab_exporter: MolabExporter = build_molab_notebook_export


DEFAULT_DEPENDENCIES = ExtractorDependencies()


def line_range_from_payload(value: Any) -> LineRange | None:
    if not isinstance(value, dict):
        return None
    start_line = value.get("startLine")
    end_line = value.get("endLine")
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return None
    return LineRange(start_line, end_line)


def source_ranges_from_payload(payload: dict[str, Any]) -> list[LineRange]:
    source_ranges = payload.get("sourceRanges") or {}
    if not isinstance(source_ranges, dict):
        return []
    config_ranges = source_ranges.get("config") or []
    if not isinstance(config_ranges, list):
        return []
    return [
        line_range
        for item in config_ranges
        if (line_range := line_range_from_payload(item)) is not None
    ]


def cell_plans(request: ExtractionRequest) -> list[CellPlan]:
    return [
        CellPlan.from_payload(index, cell, request.metadata)
        for index, cell in enumerate(request.cells)
    ]


def add_cells_to_runtime(
    runtime: Runtime,
    plans: list[CellPlan],
    filename: str,
    *,
    first_browser_cell_index: int,
) -> tuple[list[dict[str, Any] | None], list[PendingCellOutput]]:
    outputs: list[dict[str, Any] | None] = []
    pending_outputs: list[PendingCellOutput] = []
    browser_cell_index = first_browser_cell_index

    for plan in plans:
        if plan.skip_without_execution:
            outputs.append(output_model(""))
            continue
        if not plan.execute:
            outputs.append(plan.non_executed_output())
            continue

        try:
            stub = runtime.generator.add_code(
                plan.executable_source,
                display_code=plan.display_code,
                display_output=plan.display_output,
                is_reactive=True,
                is_raw=True,
            )
        except Exception as exc:
            if not as_bool(plan.config.get("error"), True):
                raise RuntimeError(
                    f"marimo execution failed in {plan.error_location(filename)}"
                ) from exc
            if not plan.display_code:
                raise
            outputs.append(plan.compile_error_output())
            continue

        runtime.apply_cell_metadata(stub, plan)
        outputs.append(None)
        pending_outputs.append(PendingCellOutput(plan, stub, browser_cell_index))
        browser_cell_index += 1

    return outputs, pending_outputs


async def build_runtime_payload(
    request: ExtractionRequest,
    runtime: Runtime,
    plans: list[CellPlan],
    header_stubs: list[Any],
    pending_outputs: list[PendingCellOutput],
    molab_exporter: MolabExporter,
) -> RuntimePayload:
    if not pending_outputs:
        return RuntimePayload(did_error=False)

    did_error = await runtime.build(request.filename)
    fail_on_header_errors(header_stubs, request.filename)
    molab_notebook_code = ""
    molab_source_fallback_reason = ""

    if request.widget_config["molab"]["enabled"]:
        molab_export = molab_exporter(
            request.source,
            plans,
            identity=request.identity,
            config_ranges=request.config_ranges,
            pyproject=request.pyproject,
            header=request.header,
        )
        molab_notebook_code = molab_export.code
        molab_source_fallback_reason = (
            molab_export.source_assembly.fallback_reason or ""
        )

    return RuntimePayload(
        did_error=did_error,
        notebook_code=runtime.export_notebook_code(request.pyproject),
        molab_notebook_code=molab_notebook_code,
        molab_source_fallback_reason=molab_source_fallback_reason,
        assets=runtime.render_assets(),
    )


def runtime_payload_index(pending_outputs: list[PendingCellOutput]) -> int | None:
    return next(
        (pending.plan.index for pending in pending_outputs if pending.plan.include),
        None,
    )


def hidden_output_for(
    pending: PendingCellOutput,
    *,
    app_id: str,
    runtime_index: int | None,
    html_prefix: str,
    payload: RuntimePayload,
    runtime_cell_count: int,
) -> dict[str, Any]:
    if runtime_index is None:
        return output_model("")
    has_runtime_payload = pending.plan.index == runtime_index
    hidden_output = hidden_runtime_output(
        pending.stub,
        pending.browser_cell_index,
        app_id,
        html_prefix=html_prefix,
    )
    if not has_runtime_payload:
        return hidden_output
    return output_model(
        hidden_output["html"],
        app_id=app_id,
        notebook_code=payload.notebook_code,
        molab_notebook_code=payload.molab_notebook_code,
        molab_source_fallback_reason=payload.molab_source_fallback_reason,
        assets=payload.assets,
        runtime_cell_count=runtime_cell_count,
    )


def fail_on_strict_error(
    pending: PendingCellOutput,
    payload: RuntimePayload,
    filename: str,
    html_output: str,
    *,
    has_server_output: bool,
) -> None:
    if as_bool(pending.plan.config.get("error"), True):
        return
    error_probe_html = (
        html_output
        if has_server_output
        else use_browser_cell_index(
            pending.stub.render(display_output=True),
            pending.browser_cell_index,
        )
    )
    if payload.did_error and has_error_mimetype(error_probe_html):
        raise RuntimeError(
            f"marimo execution failed in {pending.plan.error_location(filename)}"
        )


def render_pending_outputs(
    outputs: list[dict[str, Any] | None],
    pending_outputs: list[PendingCellOutput],
    *,
    request: ExtractionRequest,
    payload: RuntimePayload,
    header_stubs: list[Any],
) -> None:
    if not pending_outputs:
        return

    runtime_index = runtime_payload_index(pending_outputs)
    header_html = hidden_header_islands(header_stubs)
    header_output_index = pending_outputs[0].plan.index if header_html else None
    runtime_cell_count = len(header_stubs) + len(pending_outputs)

    for pending in pending_outputs:
        plan = pending.plan
        html_prefix = header_html if plan.index == header_output_index else ""

        if not plan.display_output and not plan.display_code:
            fail_on_strict_error(
                pending,
                payload,
                request.filename,
                "",
                has_server_output=False,
            )
            outputs[plan.index] = hidden_output_for(
                pending,
                app_id=request.app_id,
                runtime_index=runtime_index,
                html_prefix=html_prefix,
                payload=payload,
                runtime_cell_count=runtime_cell_count,
            )
            continue

        html_output = use_browser_cell_index(
            pending.stub.render(display_output=plan.display_server_output),
            pending.browser_cell_index,
        )
        suppress_mimetypes: set[str] = set()
        if not plan.display_output:
            html_output = hide_island_output(html_output)
        if not as_bool(plan.config.get("error"), True):
            fail_on_strict_error(
                pending,
                payload,
                request.filename,
                html_output,
                has_server_output=plan.display_server_output,
            )
            html_output = suppress_mime_renderers(html_output, ERROR_MIMETYPES)
            suppress_mimetypes = ERROR_MIMETYPES
        html_output = f"{html_prefix}{html_output}"

        has_runtime_payload = plan.index == runtime_index
        outputs[plan.index] = output_model(
            html_output,
            app_id=request.app_id,
            notebook_code=payload.notebook_code if has_runtime_payload else "",
            molab_notebook_code=payload.molab_notebook_code
            if has_runtime_payload
            else "",
            molab_source_fallback_reason=payload.molab_source_fallback_reason
            if has_runtime_payload
            else "",
            assets=payload.assets if has_runtime_payload else None,
            suppress_mimetypes=suppress_mimetypes,
            runtime_cell_count=runtime_cell_count if has_runtime_payload else None,
        )


def finalize_outputs(
    outputs: list[dict[str, Any] | None],
    widget_config: dict[str, Any],
) -> list[dict[str, Any]]:
    final_outputs: list[dict[str, Any]] = []
    for output in outputs:
        if output is None:
            raise RuntimeError("internal error: marimo output was not rendered")
        final_outputs.append({**output, "widgetConfig": widget_config})
    return final_outputs


def generated_marimo_sources(plans: list[CellPlan]) -> list[str]:
    return [
        plan.executable_source
        for plan in plans
        if plan.execute and plan.language in {"markdown", "sql"}
    ]


def executable_sources(plans: list[CellPlan]) -> list[str]:
    return [plan.executable_source for plan in plans if plan.execute]


async def extract(
    payload: dict[str, Any],
    dependencies: ExtractorDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    request = ExtractionRequest.from_payload(payload)
    plans = cell_plans(request)
    runtime = dependencies.runtime_factory(
        request.app_id,
        page_cell_prefix(request.identity),
    )
    header_stubs = add_header_cells(
        runtime.generator,
        runtime_header_sources(
            request.header,
            generated_marimo_sources(plans),
            executable_sources(plans),
        ),
    )
    outputs, pending_outputs = add_cells_to_runtime(
        runtime,
        plans,
        request.filename,
        first_browser_cell_index=len(header_stubs),
    )
    payload_model = await build_runtime_payload(
        request,
        runtime,
        plans,
        header_stubs,
        pending_outputs,
        dependencies.molab_exporter,
    )
    render_pending_outputs(
        outputs,
        pending_outputs,
        request=request,
        payload=payload_model,
        header_stubs=header_stubs,
    )

    return {
        "cells": [
            {"startLine": cell.get("startLine"), "options": cell.get("options") or {}}
            for cell in request.cells
        ],
        "outputs": finalize_outputs(outputs, request.widget_config),
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    # The executable protocol reserves stdout for JSON.
    with redirect_stdout(sys.stderr):
        result = asyncio.run(extract(payload))
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
