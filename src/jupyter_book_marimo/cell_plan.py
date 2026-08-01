"""Resolve authored cells into executable source and visibility decisions.

Each `CellPlan` combines page defaults, cell options, source conversion, and
line metadata. The extractor uses those plans for execution, rendered output,
and Molab export.
"""

from __future__ import annotations

import keyword
from dataclasses import dataclass
from typing import Any

from marimo._convert.common.format import markdown_to_marimo, sql_to_marimo

from .authoring import (
    ExecutionOptions,
    as_bool,
    normalized_options,
    resolved_execution_options,
    should_display_code,
    should_display_output,
    should_display_server_output,
    should_execute,
    should_include,
)
from .island_output import output_model, visible_code_html
from .molab import LineRange

DEFAULT_SQL_QUERY_TARGET = "_df"
RESERVED_SQL_QUERY_TARGETS = {"mo"}


def is_valid_python_identifier(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def sql_query_target(query: Any) -> str:
    """Return a valid Python target name for SQL output."""
    target = str(query or DEFAULT_SQL_QUERY_TARGET)
    if is_valid_python_identifier(target) and target not in RESERVED_SQL_QUERY_TARGETS:
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


def markdown_code_to_python(code: str) -> str:
    return markdown_to_marimo(code)


def source_for_cell(cell: dict[str, Any]) -> str:
    """Return Python source for one authored cell."""
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
        return markdown_code_to_python(code)
    return code


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
    display_server_output: bool
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
            display_server_output=should_display_server_output(config),
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
        """Return visible source for a cell that cannot become Python code."""
        return output_model(
            visible_code_html(
                self.original_code,
                self.language,
                "could not compile",
            )
        )

    def error_location(self, filename: str) -> str:
        return f"{filename}:{self.start_line}" if self.start_line else filename

    @property
    def source_range(self) -> LineRange | None:
        if self.start_line is None or self.end_line is None:
            return None
        return LineRange(self.start_line, self.end_line)
