"""Build the notebook source used by the Molab launcher."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

MolabSourceFallbackReason = Literal[
    "empty_page_source",
    "missing_source_ranges",
    "invalid_source_ranges",
    "out_of_bounds_source_ranges",
]


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


def markdown_source_for_molab(markdown: str) -> str | None:
    content = markdown.strip()
    if not content:
        return None
    return (
        "import marimo as _mo\n\n_mo.md("
        + json.dumps(
            content,
            ensure_ascii=False,
        )
        + ")"
    )


def frontmatter_end_index(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return index + 1
    return 0


def molab_source_cells_from_segments(segments: list[MolabSourceSegment]) -> list[str]:
    return [segment.source for segment in segments if segment.source is not None]


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
    """Interleave page markdown with parsed cell plans without reparsing fences."""
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
