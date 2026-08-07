"""Normalize MyST directives into the marimo page protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

from .protocol import JsonObject, MarimoCellRequest

MARIMO_CELL_NODE = "marimoCell"
MARIMO_CONFIG_NODE = "marimoConfig"

SUPPORTED_LANGUAGES = {"python", "sql", "markdown"}

BOOLEAN_OPTION_SPEC = {"type": "boolean"}
STRING_OPTION_SPEC = {"type": "string"}
NUMBER_OPTION_SPEC = {"type": "number"}
EXECUTION_OPTION_SPECS = {
    "eval": BOOLEAN_OPTION_SPEC,
    "echo": BOOLEAN_OPTION_SPEC,
    "editor": BOOLEAN_OPTION_SPEC,
    "output": BOOLEAN_OPTION_SPEC,
    "server-output": BOOLEAN_OPTION_SPEC,
    "error": BOOLEAN_OPTION_SPEC,
    "include": BOOLEAN_OPTION_SPEC,
}

MARIMO_DIRECTIVE_OPTION_SPECS = {
    **EXECUTION_OPTION_SPECS,
    "query": STRING_OPTION_SPEC,
    "engine": STRING_OPTION_SPEC,
    "hide-code": BOOLEAN_OPTION_SPEC,
    "hide-output": BOOLEAN_OPTION_SPEC,
    "disabled": BOOLEAN_OPTION_SPEC,
    "unparsable": BOOLEAN_OPTION_SPEC,
    "name": STRING_OPTION_SPEC,
    "column": NUMBER_OPTION_SPEC,
}

MARIMO_CONFIG_OPTION_SPECS = {
    **EXECUTION_OPTION_SPECS,
    "external-env": BOOLEAN_OPTION_SPEC,
    "header": STRING_OPTION_SPEC,
    "pyproject": STRING_OPTION_SPEC,
}

CELL_OPTION_KEYS = set(MARIMO_DIRECTIVE_OPTION_SPECS)
CONFIG_OPTION_KEYS = set(MARIMO_CONFIG_OPTION_SPECS)
SQL_OPTION_KEYS = {"query", "engine"}
CONFLICTING_OPTIONS = (
    ("echo", "hide-code"),
    ("output", "hide-output"),
    ("eval", "disabled"),
)


@dataclass(frozen=True)
class Cell:
    source: str
    options: JsonObject
    position: JsonObject | None = None

    def request(self, index: int) -> MarimoCellRequest:
        start_line, end_line = position_lines(self.position)
        return MarimoCellRequest(
            index=index,
            source=self.source,
            options=self.options,
            start_line=start_line,
            end_line=end_line,
        )


@dataclass(frozen=True)
class PageConfig:
    defaults: JsonObject = field(default_factory=dict)
    header: str = ""
    pyproject: str = ""
    external_env: bool = False

    def to_json(self) -> JsonObject:
        return {
            "defaults": self.defaults,
            "header": self.header,
            "pyproject": self.pyproject,
            "externalEnv": self.external_env,
        }

    @classmethod
    def from_json(cls, value: Any) -> PageConfig:
        payload = value if isinstance(value, dict) else {}
        defaults = payload.get("defaults")
        return cls(
            defaults=dict(defaults) if isinstance(defaults, dict) else {},
            header=str(payload.get("header") or ""),
            pyproject=str(payload.get("pyproject") or ""),
            external_env=as_bool(payload.get("externalEnv")),
        )


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def pyproject_to_script_metadata(pyproject: str) -> str:
    body = dedent(pyproject).strip()
    if not body:
        return ""
    if body.startswith("# /// script"):
        return f"{body}\n"

    lines = ["# /// script"]
    lines.extend(f"# {line}" if line else "#" for line in body.splitlines())
    lines.append("# ///")
    return "\n".join(lines) + "\n"


def cell_from_directive(data: dict[str, Any]) -> Cell:
    language = str(data.get("arg") or "").strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ValueError(f"marimo language must be one of: {supported}")

    options = directive_options(data)
    reject_unknown_options(options, CELL_OPTION_KEYS, directive="marimo")
    reject_conflicts(options)
    if language != "sql":
        illegal = sorted(SQL_OPTION_KEYS & set(options))
        if illegal:
            raise ValueError(
                f"SQL-only marimo option(s) on {language} cell: {', '.join(illegal)}"
            )

    return Cell(
        source=str(data.get("body") or ""),
        options=cell_options_patch(language, options),
        position=directive_position(data),
    )


def config_from_directive(data: dict[str, Any]) -> PageConfig:
    options = directive_options(data)
    if options.get("pyproject") == "":
        options = {**options, "pyproject": str(data.get("body") or "")}
    reject_unknown_options(options, CONFIG_OPTION_KEYS, directive="marimo-config")
    reject_conflicts(options)

    external_env = as_bool(options.get("external-env"))
    pyproject = str(options.get("pyproject") or "")
    if external_env and pyproject.strip():
        raise ValueError("marimo-config cannot combine external-env and pyproject")

    return PageConfig(
        defaults=execution_options_patch(options),
        header=str(options.get("header") or ""),
        pyproject=pyproject,
        external_env=external_env,
    )


def cell_from_node(node: dict[str, Any]) -> Cell | None:
    if node.get("type") != MARIMO_CELL_NODE:
        return None
    options = node.get("options")
    position = node.get("position")
    return Cell(
        source=str(node.get("value") or ""),
        options=dict(options) if isinstance(options, dict) else {},
        position=position if isinstance(position, dict) else None,
    )


def config_from_node(node: dict[str, Any]) -> PageConfig:
    return PageConfig.from_json(node.get("config"))


def cell_options_patch(language: str, options: dict[str, Any]) -> JsonObject:
    patch = execution_options_patch(options)
    patch["language"] = language

    marimo: JsonObject = {}
    disabled = as_bool(options.get("disabled"))
    unparsable = as_bool(options.get("unparsable"))
    if "disabled" in options:
        marimo["disabled"] = disabled
    if "unparsable" in options:
        marimo["unparsable"] = unparsable
    if marimo:
        patch["marimo"] = marimo
    if disabled or unparsable:
        execution = patch.setdefault("execution", {})
        execution["enabled"] = False
    if unparsable and not as_bool(options.get("hide-code")):
        render = patch.setdefault("render", {})
        render["source"] = True

    if language == "sql":
        sql: JsonObject = {}
        if "query" in options:
            sql["outputName"] = str(options["query"])
        if "engine" in options:
            sql["engine"] = str(options["engine"])
        if sql:
            patch["sql"] = sql

    if "name" in options:
        patch["name"] = str(options["name"])
    if "column" in options:
        patch["column"] = options["column"]
    return patch


def execution_options_patch(options: dict[str, Any]) -> JsonObject:
    render: JsonObject = {}
    execution: JsonObject = {}

    render_keys = {
        "echo": "source",
        "editor": "editor",
        "output": "output",
        "server-output": "serverOutput",
        "error": "error",
        "include": "include",
    }
    for source, target in render_keys.items():
        if source in options:
            render[target] = as_bool(options[source])

    if as_bool(options.get("hide-code")):
        render["source"] = False
        render["editor"] = False
    if as_bool(options.get("hide-output")):
        render["output"] = False
    if "eval" in options:
        execution["enabled"] = as_bool(options["eval"])

    patch: JsonObject = {}
    if render:
        patch["render"] = render
    if execution:
        patch["execution"] = execution
    return patch


def directive_options(data: dict[str, Any]) -> dict[str, Any]:
    options = data.get("options") or {}
    if not isinstance(options, dict):
        raise ValueError("Directive options must be a mapping")
    return dict(options)


def directive_position(data: dict[str, Any]) -> JsonObject | None:
    node = data.get("node")
    if not isinstance(node, dict):
        return None
    position = node.get("position")
    return dict(position) if isinstance(position, dict) else None


def position_lines(position: JsonObject | None) -> tuple[int | None, int | None]:
    if position is None:
        return None, None
    start = position.get("start")
    end = position.get("end")
    start_line = start.get("line") if isinstance(start, dict) else None
    end_line = end.get("line") if isinstance(end, dict) else None
    return (
        start_line if isinstance(start_line, int) else None,
        end_line if isinstance(end_line, int) else None,
    )


def reject_unknown_options(
    options: dict[str, Any],
    allowed: set[str],
    *,
    directive: str,
) -> None:
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise ValueError(f"Unsupported {directive} option(s): {', '.join(unknown)}")


def reject_conflicts(options: dict[str, Any]) -> None:
    for first, second in CONFLICTING_OPTIONS:
        if as_bool(options.get(first)) and as_bool(options.get(second)):
            raise ValueError(f"Conflicting marimo options: {first} and {second}")
