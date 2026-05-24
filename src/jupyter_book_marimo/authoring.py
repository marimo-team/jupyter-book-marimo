"""Validate MyST-native marimo directives into executable cell models."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any

ExecutionOptions = dict[str, Any]
CellOptions = dict[str, Any]

MARIMO_CELL_NODE = "marimoCell"
MARIMO_CONFIG_NODE = "marimoConfig"

SUPPORTED_LANGUAGES = {"python", "sql", "markdown"}

DEFAULT_EXECUTION_OPTIONS: ExecutionOptions = {
    "eval": True,
    "echo": False,
    "output": True,
    "error": True,
    "include": True,
    "editor": False,
}

CANONICAL_OPTION_KEYS = {
    "eval",
    "echo",
    "output",
    "error",
    "include",
    "editor",
    "query",
    "engine",
    "hide-code",
    "hide-output",
    "disabled",
    "unparsable",
    "name",
    "column",
}

CONFIG_OPTION_KEYS = {
    *DEFAULT_EXECUTION_OPTIONS,
    "external-env",
    "header",
    "molab",
    "pyproject",
}

SQL_ONLY_OPTION_KEYS = {"query", "engine"}
CONFLICTING_OPTION_KEYS = (
    ("echo", "hide-code"),
    ("output", "hide-output"),
    ("eval", "disabled"),
)


def pyproject_to_script_metadata(pyproject: str) -> str:
    """Lift document pyproject metadata into marimo's script metadata form."""
    body = dedent(pyproject).strip()
    if not body:
        return ""
    if body.startswith("# /// script"):
        return f"{body}\n"

    commented_lines = ["# /// script"]
    for line in body.splitlines():
        commented_lines.append(f"# {line}" if line else "#")
    commented_lines.append("# ///")
    return "\n".join(commented_lines) + "\n"


def internal_key(key: str) -> str:
    return key.replace("-", "_")


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def normalized_options(options: dict[str, Any]) -> ExecutionOptions:
    """Normalize canonical MyST option spelling at the plugin boundary."""
    return {internal_key(key): value for key, value in options.items()}


def resolved_execution_options(
    document_options: dict[str, Any],
    cell_options: dict[str, Any] | None = None,
) -> ExecutionOptions:
    """Layer cell options over document options over the shared defaults."""
    return {
        **DEFAULT_EXECUTION_OPTIONS,
        **normalized_options(document_options),
        **normalized_options(cell_options or {}),
    }


def should_execute(config: ExecutionOptions) -> bool:
    return (
        as_bool(config.get("eval"), True)
        and not as_bool(config.get("disabled"))
        and not as_bool(config.get("unparsable"))
    )


def should_include(config: ExecutionOptions) -> bool:
    return as_bool(config.get("include"), True)


def should_display_code(config: ExecutionOptions) -> bool:
    if not should_include(config) or as_bool(config.get("hide_code")):
        return False
    return as_bool(config.get("echo")) or as_bool(config.get("editor"))


def should_display_output(config: ExecutionOptions) -> bool:
    return (
        should_include(config)
        and as_bool(config.get("output"), True)
        and not as_bool(config.get("hide_output"))
    )


@dataclass
class Cell:
    """One executable authoring unit plus the MyST position that produced it."""

    code: str
    options: CellOptions
    position: dict[str, Any] | None = None

    @property
    def start_line(self) -> int | None:
        line = ((self.position or {}).get("start") or {}).get("line")
        return line if isinstance(line, int) else None

    def payload(self) -> dict[str, Any]:
        return {
            "startLine": self.start_line,
            "options": self.options,
            "code": self.code,
        }


def _directive_options(data: dict[str, Any]) -> dict[str, Any]:
    options = data.get("options") or {}
    if not isinstance(options, dict):
        raise ValueError("Directive options must be a mapping")
    return options


def _position(data: dict[str, Any]) -> dict[str, Any] | None:
    node = data.get("node")
    if not isinstance(node, dict):
        return None
    position = node.get("position")
    return position if isinstance(position, dict) else None


def _reject_unknown_options(
    options: dict[str, Any],
    allowed: set[str],
    *,
    directive: str,
) -> None:
    unknown = sorted(set(options) - allowed)
    if unknown:
        formatted = ", ".join(unknown)
        raise ValueError(f"Unsupported {directive} option(s): {formatted}")


def _reject_conflicts(options: dict[str, Any]) -> None:
    for first, second in CONFLICTING_OPTION_KEYS:
        if as_bool(options.get(first)) and as_bool(options.get(second)):
            raise ValueError(f"Conflicting marimo options: {first} and {second}")


def _normalize_cell_options(options: dict[str, Any], language: str) -> CellOptions:
    _reject_unknown_options(options, CANONICAL_OPTION_KEYS, directive="marimo")
    _reject_conflicts(options)
    if language != "sql":
        illegal_sql = sorted(SQL_ONLY_OPTION_KEYS & set(options))
        if illegal_sql:
            formatted = ", ".join(illegal_sql)
            raise ValueError(
                f"SQL-only marimo option(s) on {language} cell: {formatted}"
            )
    return {"language": language, **normalized_options(options)}


def cell_from_directive(data: dict[str, Any]) -> Cell:
    """Convert parsed MyST directive data into an executable marimo cell."""
    language = str(data.get("arg") or "").strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ValueError(
            f"Unsupported marimo language: {language!r}; expected {supported}"
        )

    options = _normalize_cell_options(_directive_options(data), language)
    return Cell(
        code=str(data.get("body") or ""),
        options=options,
        position=_position(data),
    )


def config_from_directive(data: dict[str, Any]) -> dict[str, Any]:
    """Convert parsed MyST directive data into page-level marimo config."""
    options = _directive_options(data)
    _reject_unknown_options(options, CONFIG_OPTION_KEYS, directive="marimo-config")
    _reject_conflicts(options)
    if (
        as_bool(options.get("external-env"))
        and str(options.get("pyproject") or "").strip()
    ):
        raise ValueError("marimo-config cannot combine external-env and pyproject")
    return normalized_options(options)


def cell_from_node(node: dict[str, Any]) -> Cell | None:
    if node.get("type") != MARIMO_CELL_NODE:
        return None
    return Cell(
        code=str(node.get("value") or ""),
        options=dict(node.get("options") or {}),
        position=node.get("position")
        if isinstance(node.get("position"), dict)
        else None,
    )
