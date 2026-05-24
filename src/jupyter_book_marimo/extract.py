#!/usr/bin/env python3
"""Execute collected marimo cells and serialize hydratable islands.

The extractor owns marimo-specific behavior: language conversion, execution
planning, runtime asset capture, browser cell IDs, and per-cell output models.
"""

from __future__ import annotations

import asyncio
import ast
import hashlib
import html
import json
import keyword
import re
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from textwrap import dedent
from typing import Any

import marimo
from marimo import MarimoIslandGenerator
from marimo._ast.cell import CellConfig
from marimo._ast.cell_manager import CellManager
from marimo._convert.common.format import markdown_to_marimo, sql_to_marimo
from marimo._session.notebook import AppFileManager
from marimo._session.notebook.storage import FilesystemStorage

from .authoring import (
    ExecutionOptions,
    as_bool,
    normalized_options,
    resolved_execution_options,
    should_display_code,
    should_display_output,
    should_execute,
    should_include,
    pyproject_to_script_metadata,
)
from .molab import (
    LineRange,
    MolabSourceAssembly,
    MolabSourceReplacement,
    MolabSourceSegment,
    assemble_molab_source_cells as assemble_molab_source_segments,
    markdown_source_for_molab,
    molab_source_replacement_plan as plan_molab_source_replacements,
)

MIN_MARIMO_VERSION = "0.23.5"
ERROR_MIMETYPES = {
    "application/vnd.marimo+error",
    "application/vnd.marimo+traceback",
}
DEFAULT_SQL_QUERY_TARGET = "_df"


def version_tuple(version: str) -> tuple[int, int, int]:
    """Compare marimo versions without pulling in packaging at runtime."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        return (0, 0, 0)
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


if version_tuple(marimo.__version__) < version_tuple(MIN_MARIMO_VERSION):
    raise RuntimeError(
        f"jupyter-book-marimo requires marimo >= {MIN_MARIMO_VERSION}, "
        f"got {marimo.__version__}"
    )


class ReadOnlyFilesystemStorage(FilesystemStorage):
    """Preserve source-relative reads while no-oping save/rename side effects."""

    def write(self, path: Path, content: str) -> None:  # noqa: ARG002
        return None

    def rename(self, old_path: Path, new_path: Path) -> None:  # noqa: ARG002
        return None


class HeadAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.module_scripts: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "script" and values.get("type") == "module" and values.get("src"):
            self.module_scripts.append(values["src"])
        elif tag == "link" and values.get("href"):
            self.links.append(values)


class AttributeParser(HTMLParser):
    """Read attributes from one rendered HTML tag without a DOM dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.attrs: dict[str, str] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.attrs = {key: value or "" for key, value in attrs}


def is_valid_python_identifier(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def sql_query_target(query: Any) -> str:
    """Default unsafe or missing SQL output names to a predictable variable."""
    target = str(query or DEFAULT_SQL_QUERY_TARGET)
    if is_valid_python_identifier(target):
        return target
    return DEFAULT_SQL_QUERY_TARGET


def as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sql_code_to_python(
    code: str,
    query: Any,
    hide_output: bool = False,
    engine: str | None = None,
) -> str:
    return sql_to_marimo(code, sql_query_target(query), hide_output, engine)


def source_for_cell(cell: dict[str, Any]) -> str:
    """Convert SQL and Markdown authoring cells before marimo sees them."""
    options = normalized_options(cell.get("options") or {})
    code = str(cell.get("code") or "")
    language = str(options.get("language") or "python").lower()

    if language == "sql":
        return sql_code_to_python(
            code,
            options.get("query"),
            as_bool(options.get("hide_output")),
            str(options["engine"]) if options.get("engine") else None,
        )
    if language == "markdown":
        return markdown_to_marimo(code)
    return code


def visible_code_html(code: str, language: str, message: str | None = None) -> str:
    escaped = html.escape(code)
    note = (
        f'<div class="marimo-plugin-note">{html.escape(message)}</div>'
        if message
        else ""
    )
    return (
        '<div class="marimo-plugin-fallback">'
        f'{note}<pre><code class="language-{html.escape(language)}">'
        f"{escaped}</code></pre></div>"
    )


def use_browser_cell_index(island: str, cell_index: int) -> str:
    """Use browser-local cell indexes for reactive islands.

    The server export and the browser Pyodide runtime do not share generated
    cell IDs. marimo islands can instead resolve cells by index after the
    runtime loads the notebook code.
    """
    return re.sub(
        r'\s+data-cell-id="[^"]+"',
        f'\n    data-cell-idx="{cell_index}"',
        island,
        count=1,
    )


def output_model(
    html: str,
    *,
    app_id: str = "",
    notebook_code: str = "",
    molab_notebook_code: str = "",
    molab_source_fallback_reason: str = "",
    assets: dict[str, Any] | None = None,
    suppress_mimetypes: set[str] | None = None,
) -> dict[str, Any]:
    model: dict[str, Any] = {"html": html}
    if app_id:
        model["appId"] = app_id
    if notebook_code:
        model["notebookCode"] = notebook_code
    if molab_notebook_code:
        model["molabNotebookCode"] = molab_notebook_code
    if molab_source_fallback_reason:
        model["molabSourceFallbackReason"] = molab_source_fallback_reason
    if assets:
        model["assets"] = assets
    if suppress_mimetypes:
        model["suppressMimetypes"] = sorted(suppress_mimetypes)
    return model


def widget_config_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {"molab": {"enabled": as_bool(metadata.get("molab"), default=True)}}


@dataclass(frozen=True)
class CellPlan:
    """Resolved execution and visibility decisions for one authored cell."""

    index: int
    start_line: int | None
    end_line: int | None
    config: ExecutionOptions
    language: str
    original_code: str
    executable_source: str
    include: bool
    display_code: bool
    display_output: bool
    execute: bool
    disabled: bool
    unparsable: bool
    hide_code: bool
    column: int | None
    name: str | None

    @classmethod
    def from_payload(
        cls,
        index: int,
        cell: dict[str, Any],
        document_options: dict[str, Any],
    ) -> CellPlan:
        options = normalized_options(cell.get("options") or {})
        config = resolved_execution_options(document_options, options)
        language = str(options.get("language") or "python").lower()
        start_line = cell.get("startLine")
        end_line = cell.get("endLine")
        return cls(
            index=index,
            start_line=start_line if isinstance(start_line, int) else None,
            end_line=end_line if isinstance(end_line, int) else None,
            config=config,
            language=language,
            original_code=str(cell.get("code") or ""),
            executable_source=source_for_cell(cell),
            include=should_include(config),
            display_code=should_display_code(config),
            display_output=should_display_output(config),
            execute=should_execute(config),
            disabled=as_bool(config.get("disabled")),
            unparsable=as_bool(config.get("unparsable")),
            hide_code=as_bool(config.get("hide_code")),
            column=as_int(config.get("column")),
            name=str(config["name"]) if config.get("name") else None,
        )

    @property
    def skip_without_execution(self) -> bool:
        return not self.include and not self.execute

    def non_executed_output(self) -> dict[str, Any]:
        message = None
        if self.disabled:
            message = "disabled"
        elif self.unparsable:
            message = "unparsable"
        return output_model(
            visible_code_html(self.original_code, self.language, message)
            if self.display_code
            else ""
        )

    def compile_error_output(self) -> dict[str, Any]:
        """Show source when an echo/editor cell cannot become Python code."""
        return output_model(
            visible_code_html(
                self.original_code,
                self.language,
                "could not compile",
            )
        )

    @property
    def source_range(self) -> "LineRange | None":
        if self.start_line is None or self.end_line is None:
            return None
        return LineRange(self.start_line, self.end_line)

    def molab_source(self) -> str | None:
        if self.execute:
            return self.executable_source
        if not self.display_code:
            return None
        return markdown_source_for_molab(
            f"```{self.language}\n{self.original_code}\n```"
        )


@dataclass(frozen=True)
class PendingCellOutput:
    plan: CellPlan
    stub: Any


@dataclass(frozen=True)
class MolabNotebookExport:
    code: str
    source_assembly: MolabSourceAssembly


def normalized_mimetype(value: str) -> str:
    """Match marimo's escaped MIME attributes against plugin options."""
    return html.unescape(value).strip().strip("\"'")


def renderer_mimetype(tag: str) -> str:
    parser = AttributeParser()
    parser.feed(tag)
    return normalized_mimetype(parser.attrs.get("data-mime", ""))


def suppress_mime_renderers(island: str, mimetypes: set[str]) -> str:
    if not mimetypes:
        return island

    def keep_or_remove(match: re.Match[str]) -> str:
        tag = match.group(0)
        return "" if renderer_mimetype(tag) in mimetypes else tag

    return re.sub(
        r"<marimo-mime-renderer\b[^>]*>.*?</marimo-mime-renderer>",
        keep_or_remove,
        island,
        flags=re.DOTALL,
    )


def has_error_mimetype(island: str) -> bool:
    return any(
        renderer_mimetype(match.group(0)) in ERROR_MIMETYPES
        for match in re.finditer(
            r"<marimo-mime-renderer\b[^>]*>.*?</marimo-mime-renderer>",
            island,
            flags=re.DOTALL,
        )
    )


def page_digest(filename: str) -> str:
    """Keep app and cell IDs stable without leaking long source paths."""
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]


def page_cell_prefix(filename: str) -> str:
    return f"jb{page_digest(filename)}"


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


def molab_source_segments_from_plans(plans: list[CellPlan]) -> list[MolabSourceSegment]:
    return [
        MolabSourceSegment(plan.source_range, plan.molab_source()) for plan in plans
    ]


def molab_source_cells_from_plans(plans: list[CellPlan]) -> list[str]:
    return [
        segment.source
        for segment in molab_source_segments_from_plans(plans)
        if segment.source is not None
    ]


def molab_source_replacements(
    plans: list[CellPlan],
    config_ranges: list[LineRange],
) -> list[MolabSourceReplacement] | None:
    replacement_plan = plan_molab_source_replacements(
        molab_source_segments_from_plans(plans),
        config_ranges,
    )
    if replacement_plan.fallback_reason is not None:
        return None
    return list(replacement_plan.replacements)


def assemble_molab_source_cells(
    source: str,
    plans: list[CellPlan],
    config_ranges: list[LineRange] | None = None,
) -> MolabSourceAssembly:
    return assemble_molab_source_segments(
        source,
        molab_source_segments_from_plans(plans),
        config_ranges,
    )


def molab_source_cells_from_page_source(
    source: str,
    plans: list[CellPlan],
    config_ranges: list[LineRange] | None = None,
) -> list[str]:
    return list(
        assemble_molab_source_cells(
            source,
            plans,
            config_ranges,
        ).source_cells
    )


def build_export_notebook_code(
    generator: MarimoIslandGenerator,
    pyproject: str,
    *,
    cell_prefix: str | None = None,
    header: str = "",
) -> str:
    """Add page header/script metadata to marimo's exported notebook source."""
    notebook_code = AppFileManager.from_app(generator._app).to_code()
    if cell_prefix is not None:
        notebook_code = install_browser_cell_prefix(notebook_code, cell_prefix)
    header = dedent(header).strip()
    script_metadata = pyproject_to_script_metadata(pyproject)
    if header:
        notebook_code = f"{header}\n\n{notebook_code}"
    if script_metadata:
        notebook_code = f"{script_metadata}{notebook_code}"
    return notebook_code


def build_molab_notebook_export(
    source: str,
    plans: list[CellPlan],
    *,
    identity: str,
    config_ranges: list[LineRange] | None = None,
    pyproject: str = "",
    header: str = "",
) -> MolabNotebookExport:
    generator = MarimoIslandGenerator(app_id="molab-" + page_digest(identity))
    source_assembly = assemble_molab_source_cells(
        source,
        plans,
        config_ranges,
    )
    for source_cell in source_assembly.source_cells:
        generator.add_code(
            source_cell,
            display_code=True,
            display_output=True,
            is_reactive=True,
            is_raw=True,
        )
    return MolabNotebookExport(
        build_export_notebook_code(
            generator,
            pyproject,
            header=header,
        ),
        source_assembly,
    )


def build_molab_notebook_code(
    source: str,
    plans: list[CellPlan],
    *,
    identity: str,
    config_ranges: list[LineRange] | None = None,
    pyproject: str = "",
    header: str = "",
) -> str:
    return build_molab_notebook_export(
        source,
        plans,
        identity=identity,
        config_ranges=config_ranges,
        pyproject=pyproject,
        header=header,
    ).code


def install_browser_cell_prefix(notebook_code: str, cell_prefix: str) -> str:
    """Install the same CellManager prefix used by server-rendered islands.

    The server HTML is rewritten to `data-cell-idx`; when the browser runtime
    rebuilds cells, this prefix makes index-resolved cell IDs match the DOM IDs
    expected by marimo plugins.
    """
    try:
        tree = ast.parse(notebook_code)
    except SyntaxError as exc:
        raise ValueError("Could not parse marimo code") from exc

    marimo_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "marimo"
    }
    if not marimo_names:
        raise ValueError("Could not find marimo import in marimo code")

    app_constructor_end: int | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not (
            isinstance(target, ast.Name)
            and target.id == "app"
            and isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "App"
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id in marimo_names
        ):
            continue
        app_constructor_end = node.end_lineno
        break
    if app_constructor_end is None:
        raise ValueError("Could not install browser cell prefix in marimo code")

    import_line = "from marimo._ast.cell_manager import CellManager\n"
    prefix_line = f"app._cell_manager = CellManager(prefix={json.dumps(cell_prefix)})\n"
    if prefix_line in notebook_code:
        return notebook_code

    lines = notebook_code.splitlines(keepends=True)
    insertions: list[tuple[int, str]] = [(app_constructor_end, prefix_line)]
    if import_line not in notebook_code:
        import_line_index = max(
            node.end_lineno or node.lineno
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name == "marimo"
        )
        insertions.append((import_line_index, import_line))

    for index, text in sorted(insertions, reverse=True):
        lines.insert(index, text)
    return "".join(lines)


def render_assets(generator: MarimoIslandGenerator) -> dict[str, Any]:
    parser = HeadAssetParser()
    parser.feed(generator.render_head(version_override=marimo.__version__))
    return {
        "moduleScripts": parser.module_scripts,
        "links": parser.links,
    }


def apply_cell_metadata(
    generator: MarimoIslandGenerator,
    stub: Any,
    plan: CellPlan,
) -> None:
    """Persist directive cell metadata into marimo's notebook model."""
    manager = generator._app.cell_manager
    cell_id = stub._cell_id
    cell = manager._compiled_cells.get(cell_id)
    notebook_cell = manager.document.get_cell(cell_id)

    config = CellConfig(
        column=plan.column,
        disabled=plan.disabled,
        hide_code=plan.hide_code,
    )
    notebook_cell.config = config
    if cell is not None:
        cell._cell.configure(config)

    if plan.name:
        notebook_cell.name = plan.name
        if cell is not None:
            cell._name = plan.name


async def build_generator(generator: MarimoIslandGenerator, filename: str) -> bool:
    from marimo._server.export import run_app_until_completion

    if generator.has_run:
        raise ValueError("marimo generator can only be built once")

    # marimo's exporter needs a file manager, but this plugin must not rewrite
    # docs sources. The private assignments give marimo a source-relative
    # filename and then connect each island stub to the completed session view.
    file_manager = AppFileManager.from_app(generator._app)
    file_manager.storage = ReadOnlyFilesystemStorage()
    file_manager.filename = filename
    file_manager.app._app._filename = filename
    session, did_error = await run_app_until_completion(
        file_manager=file_manager,
        cli_args={},
        argv=None,
        persist_session=False,
    )
    generator.has_run = True

    for stub in generator._stubs:
        stub._internal_app = generator._app
        stub._session_view = session
    return did_error


async def extract(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    cells = payload.get("cells") or []
    filename = str(payload.get("file") or "")
    identity = str(payload.get("identity") or filename)
    source = str(payload.get("source") or "")
    document_options = metadata if isinstance(metadata, dict) else {}
    config_ranges = source_ranges_from_payload(payload)
    widget_config = widget_config_from_metadata(document_options)
    app_id = "jb-" + page_digest(identity)
    generator = MarimoIslandGenerator(app_id=app_id)
    # Keep server-side IDs in the same namespace the browser runtime will use
    # after it maps each island's `data-cell-idx` back to a generated cell ID.
    generator._app._app._cell_manager = CellManager(prefix=page_cell_prefix(identity))
    outputs: list[dict[str, Any] | None] = []
    pending_outputs: list[PendingCellOutput] = []
    plans: list[CellPlan] = []

    for index, cell in enumerate(cells):
        plan = CellPlan.from_payload(index, cell, document_options)
        plans.append(plan)
        if plan.skip_without_execution:
            outputs.append(output_model(""))
            continue
        if not plan.execute:
            outputs.append(plan.non_executed_output())
            continue

        try:
            stub = generator.add_code(
                plan.executable_source,
                display_code=plan.display_code,
                display_output=plan.display_output,
                is_reactive=True,
                is_raw=True,
            )
        except Exception:
            if not plan.display_code:
                raise
            outputs.append(plan.compile_error_output())
            continue

        apply_cell_metadata(generator, stub, plan)
        outputs.append(None)
        pending_outputs.append(PendingCellOutput(plan, stub))

    if pending_outputs:
        did_error = await build_generator(generator, filename)
        notebook_code = build_export_notebook_code(
            generator,
            str(metadata.get("pyproject") or ""),
            cell_prefix=page_cell_prefix(identity),
            header=str(metadata.get("header") or ""),
        )
        molab_export = build_molab_notebook_export(
            source,
            plans,
            identity=identity,
            config_ranges=config_ranges,
            pyproject=str(metadata.get("pyproject") or ""),
            header=str(metadata.get("header") or ""),
        )
        molab_notebook_code = molab_export.code
        molab_source_fallback_reason = (
            molab_export.source_assembly.fallback_reason or ""
        )
        assets = render_assets(generator)
    else:
        did_error = False
        notebook_code = ""
        molab_notebook_code = ""
        molab_source_fallback_reason = ""
        assets = {}

    # Only the first included island carries notebook code and runtime assets;
    # later islands share the appId and wait for that app to become ready.
    runtime_payload_index = next(
        (pending.plan.index for pending in pending_outputs if pending.plan.include),
        None,
    )
    for cell_index, pending in enumerate(pending_outputs):
        plan = pending.plan
        html_output = use_browser_cell_index(pending.stub.render(), cell_index)
        if not as_bool(plan.config.get("error"), True):
            # `error: false` is build-strict only for actual execution errors.
            # Non-error outputs can still contain stale error MIME nodes.
            if did_error and has_error_mimetype(html_output):
                location = (
                    f"{filename}:{plan.start_line}" if plan.start_line else filename
                )
                raise RuntimeError(f"marimo execution failed in {location}")
            html_output = suppress_mime_renderers(html_output, ERROR_MIMETYPES)
        if not plan.include:
            outputs[plan.index] = output_model("")
            continue
        has_runtime_payload = plan.index == runtime_payload_index
        outputs[plan.index] = output_model(
            html_output,
            app_id=app_id,
            notebook_code=notebook_code if has_runtime_payload else "",
            molab_notebook_code=molab_notebook_code if has_runtime_payload else "",
            molab_source_fallback_reason=molab_source_fallback_reason
            if has_runtime_payload
            else "",
            assets=assets if has_runtime_payload else None,
        )

    final_outputs: list[dict[str, Any]] = []
    for output in outputs:
        if output is None:
            raise RuntimeError("internal error: marimo output was not rendered")
        final_outputs.append({**output, "widgetConfig": widget_config})

    return {
        "cells": [
            {"startLine": cell.get("startLine"), "options": cell.get("options") or {}}
            for cell in cells
        ],
        "outputs": final_outputs,
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    # Keep the subprocess protocol clean: stdout is JSON, user stdout is stderr.
    with redirect_stdout(sys.stderr):
        result = asyncio.run(extract(payload))
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
