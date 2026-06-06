"""Assemble notebook code for the page-level Molab launcher.

Molab opens generated notebook code outside the static book. The export combines page
Markdown, converted marimo directives, headers, and page-local script metadata.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from collections import Counter
from dataclasses import dataclass, field
import json
import re
from typing import Any, Literal, Protocol

from marimo import MarimoIslandGenerator

from .header_cells import add_header_cells, runtime_header_sources
from .runtime import build_export_notebook_code, page_digest

MolabSourceFallbackReason = Literal[
    "empty_page_source",
    "missing_source_ranges",
    "invalid_source_ranges",
    "out_of_bounds_source_ranges",
]
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE_LINE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class LineRange:
    start_line: int
    end_line: int

    @property
    def start_index(self) -> int:
        return self.start_line - 1

    @property
    def end_index(self) -> int:
        return self.end_line


@dataclass(frozen=True)
class MolabSourceSegment:
    line_range: LineRange | None
    source: str | None


@dataclass(frozen=True)
class MolabSourceReplacement:
    line_range: LineRange
    source: str | None


@dataclass(frozen=True)
class MolabSourceReplacementPlan:
    replacements: tuple[MolabSourceReplacement, ...]
    fallback_reason: MolabSourceFallbackReason | None = None


@dataclass(frozen=True)
class MolabSourceAssembly:
    source_cells: tuple[str, ...]
    fallback_reason: MolabSourceFallbackReason | None = None

    @property
    def used_page_source(self) -> bool:
        return self.fallback_reason is None


class MolabSourcePlan(Protocol):
    @property
    def source_range(self) -> LineRange | None: ...

    @property
    def execute(self) -> bool: ...

    @property
    def display_code(self) -> bool: ...

    @property
    def language(self) -> str: ...

    @property
    def original_code(self) -> str: ...

    @property
    def executable_source(self) -> str: ...


@dataclass(frozen=True)
class MolabNotebookExport:
    code: str
    source_assembly: MolabSourceAssembly


def default_molab_generator(app_id: str) -> MarimoIslandGenerator:
    return MarimoIslandGenerator(app_id=app_id)


@dataclass(frozen=True)
class MolabExportDependencies:
    """Runtime hooks used to construct a Molab notebook export."""

    generator: Callable[[str], MarimoIslandGenerator] = field(
        default=default_molab_generator
    )
    header_sources: Callable[
        [str, list[str], list[str] | None],
        tuple[str, ...],
    ] = field(default=runtime_header_sources)
    add_headers: Callable[[MarimoIslandGenerator, tuple[str, ...]], list[Any]] = field(
        default=add_header_cells
    )
    export_code: Callable[[MarimoIslandGenerator, str], str] = field(
        default=build_export_notebook_code
    )


def markdown_source_for_molab(markdown: str) -> str | None:
    content = strip_non_rendered_markdown(markdown).strip()
    if not content:
        return None
    return "mo.md(" + json.dumps(content, ensure_ascii=False) + ")"


def strip_non_rendered_markdown(markdown: str) -> str:
    output: list[str] = []
    prose_lines: list[str] = []
    fence: tuple[str, int] | None = None

    def flush_prose() -> None:
        segment = HTML_COMMENT_RE.sub("", "".join(prose_lines))
        output.extend(
            line
            for line in segment.splitlines(keepends=True)
            if not line.lstrip().startswith("%")
        )
        prose_lines.clear()

    for line in markdown.splitlines(keepends=True):
        marker = markdown_fence_marker(line)
        if fence is not None:
            output.append(line)
            if marker is not None and marker[0] == fence[0] and marker[1] >= fence[1]:
                fence = None
            continue
        if marker is not None:
            flush_prose()
            output.append(line)
            fence = marker
            continue
        prose_lines.append(line)

    flush_prose()
    return "".join(output)


def markdown_fence_marker(line: str) -> tuple[str, int] | None:
    match = FENCE_LINE_RE.match(line)
    if match is None:
        return None
    marker = match.group(1)
    return marker[0], len(marker)


def frontmatter_end_index(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return index + 1
    return 0


def molab_source_cells_from_segments(segments: list[MolabSourceSegment]) -> list[str]:
    return [segment.source for segment in segments if segment.source is not None]


def molab_source_from_plan(plan: MolabSourcePlan) -> str | None:
    if plan.execute:
        return plan.executable_source
    if not plan.display_code:
        return None
    return markdown_source_for_molab(f"```{plan.language}\n{plan.original_code}\n```")


def molab_source_segments_from_plans(
    plans: Sequence[MolabSourcePlan],
) -> list[MolabSourceSegment]:
    return [
        MolabSourceSegment(plan.source_range, molab_source_from_plan(plan))
        for plan in plans
    ]


def molab_source_cells_from_plans(plans: Sequence[MolabSourcePlan]) -> list[str]:
    return [
        segment.source
        for segment in molab_source_segments_from_plans(plans)
        if segment.source is not None
    ]


def generated_molab_marimo_sources(
    source_assembly: MolabSourceAssembly,
    plans: Sequence[MolabSourcePlan],
) -> list[str]:
    segments = molab_source_segments_from_plans(plans)
    plan_source_counts: Counter[str] = Counter()
    generated_sources: list[str] = []

    for plan, segment in zip(plans, segments, strict=True):
        if segment.source is None:
            continue
        plan_source_counts[segment.source] += 1
        if plan.language in {"markdown", "sql"} or not plan.execute:
            generated_sources.append(segment.source)

    for source_cell in source_assembly.source_cells:
        if plan_source_counts[source_cell] > 0:
            plan_source_counts[source_cell] -= 1
        else:
            generated_sources.append(source_cell)

    return generated_sources


def molab_source_replacement_plan(
    segments: list[MolabSourceSegment],
    config_ranges: list[LineRange],
) -> MolabSourceReplacementPlan:
    replacements: list[MolabSourceReplacement] = [
        MolabSourceReplacement(line_range, None) for line_range in config_ranges
    ]
    for segment in segments:
        if segment.line_range is None:
            return MolabSourceReplacementPlan((), "missing_source_ranges")
        replacements.append(MolabSourceReplacement(segment.line_range, segment.source))

    replacements.sort(key=lambda replacement: replacement.line_range.start_line)
    previous_end = 0
    for replacement in replacements:
        if (
            replacement.line_range.start_line < 1
            or replacement.line_range.end_line < replacement.line_range.start_line
            or replacement.line_range.start_index < previous_end
        ):
            return MolabSourceReplacementPlan((), "invalid_source_ranges")
        previous_end = replacement.line_range.end_index
    return MolabSourceReplacementPlan(tuple(replacements))


def molab_source_fallback_assembly(
    segments: list[MolabSourceSegment],
    reason: MolabSourceFallbackReason,
) -> MolabSourceAssembly:
    return MolabSourceAssembly(
        tuple(molab_source_cells_from_segments(segments)), reason
    )


def assemble_molab_source_cells(
    source: str,
    segments: list[MolabSourceSegment],
    config_ranges: list[LineRange] | None = None,
) -> MolabSourceAssembly:
    """Replace directive source ranges with executable marimo cells."""
    if not source.strip():
        return molab_source_fallback_assembly(segments, "empty_page_source")

    replacement_plan = molab_source_replacement_plan(segments, config_ranges or [])
    if replacement_plan.fallback_reason is not None:
        return molab_source_fallback_assembly(
            segments,
            replacement_plan.fallback_reason,
        )

    lines = source.splitlines(keepends=True)
    sources: list[str] = []
    cursor = frontmatter_end_index(lines)
    for replacement in replacement_plan.replacements:
        start_index = replacement.line_range.start_index
        end_index = replacement.line_range.end_index
        if start_index < cursor or end_index > len(lines):
            return molab_source_fallback_assembly(
                segments,
                "out_of_bounds_source_ranges",
            )

        markdown_source = markdown_source_for_molab("".join(lines[cursor:start_index]))
        if markdown_source is not None:
            sources.append(markdown_source)
        if replacement.source is not None:
            sources.append(replacement.source)
        cursor = end_index

    markdown_source = markdown_source_for_molab("".join(lines[cursor:]))
    if markdown_source is not None:
        sources.append(markdown_source)
    return MolabSourceAssembly(tuple(sources))


def molab_source_replacements(
    plans: Sequence[MolabSourcePlan],
    config_ranges: list[LineRange],
) -> list[MolabSourceReplacement] | None:
    replacement_plan = molab_source_replacement_plan(
        molab_source_segments_from_plans(plans),
        config_ranges,
    )
    if replacement_plan.fallback_reason is not None:
        return None
    return list(replacement_plan.replacements)


def assemble_molab_source_cells_from_plans(
    source: str,
    plans: Sequence[MolabSourcePlan],
    config_ranges: list[LineRange] | None = None,
) -> MolabSourceAssembly:
    return assemble_molab_source_cells(
        source,
        molab_source_segments_from_plans(plans),
        config_ranges,
    )


def molab_source_cells_from_page_source(
    source: str,
    plans: Sequence[MolabSourcePlan],
    config_ranges: list[LineRange] | None = None,
) -> list[str]:
    return list(
        assemble_molab_source_cells_from_plans(
            source,
            plans,
            config_ranges,
        ).source_cells
    )


def build_molab_notebook_export(
    source: str,
    plans: Sequence[MolabSourcePlan],
    *,
    identity: str,
    config_ranges: list[LineRange] | None = None,
    pyproject: str = "",
    header: str = "",
    dependencies: MolabExportDependencies | None = None,
) -> MolabNotebookExport:
    deps = dependencies or MolabExportDependencies()
    generator = deps.generator("molab-" + page_digest(identity))
    source_assembly = assemble_molab_source_cells_from_plans(
        source,
        plans,
        config_ranges,
    )
    deps.add_headers(
        generator,
        deps.header_sources(
            header,
            generated_molab_marimo_sources(source_assembly, plans),
            list(source_assembly.source_cells),
        ),
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
        deps.export_code(generator, pyproject),
        source_assembly,
    )


def build_molab_notebook_code(
    source: str,
    plans: Sequence[MolabSourcePlan],
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
