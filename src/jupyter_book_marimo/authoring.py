"""Parse marimo-flavoured MyST authoring into executable cells."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any

import yaml

ExecutionOptions = dict[str, Any]

CellOptions = dict[str, str | int | float | bool | None]

DEFAULT_EXECUTION_OPTIONS: ExecutionOptions = {
    "eval": True,
    "echo": False,
    "output": True,
    "warning": True,
    "error": True,
    "include": True,
    "editor": False,
}

PAGE_EXECUTION_OPTION_KEYS = (
    *DEFAULT_EXECUTION_OPTIONS.keys(),
    "hide_code",
    "hide_output",
    "disabled",
    "unparseable",
    "unparsable",
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


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def normalized_options(options: dict[str, Any]) -> ExecutionOptions:
    return {key.replace("-", "_"): value for key, value in options.items()}


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


def is_unparseable(config: ExecutionOptions) -> bool:
    return as_bool(config.get("unparseable")) or as_bool(config.get("unparsable"))


def should_execute(config: ExecutionOptions) -> bool:
    return (
        as_bool(config.get("eval"), True)
        and not as_bool(config.get("disabled"))
        and not is_unparseable(config)
    )


def should_include(config: ExecutionOptions) -> bool:
    return as_bool(config.get("include"), True)


def should_display_code(config: ExecutionOptions) -> bool:
    if not should_include(config) or as_bool(config.get("hide_code")):
        return False
    # marimo currently exposes one island flag for visible code. `echo` is the
    # Quarto execution option; `editor` is retained as a display-code request
    # until marimo exposes a separate browser editor affordance for islands.
    return as_bool(config.get("echo")) or as_bool(config.get("editor"))


def should_display_output(config: ExecutionOptions) -> bool:
    return (
        should_include(config)
        and as_bool(config.get("output"), True)
        and not as_bool(config.get("hide_output"))
    )


@dataclass
class Cell:
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


@dataclass
class SourceFence:
    start_line: int
    language: str
    code: str
    options: CellOptions


@dataclass
class SourcePage:
    metadata: dict[str, Any]
    fences: list[SourceFence]
    path: Path | None = None


FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)


def _unquote(value: str) -> str:
    if len(value) < 2:
        return value
    quote = value[0]
    if quote not in {"'", '"'} or value[-1] != quote:
        return value
    return value[1:-1].replace(f"\\{quote}", quote).replace("\\\\", "\\")


def parse_scalar(value: Any) -> str | int | float | bool | None:
    if value is None:
        return ""
    if isinstance(value, bool | int | float):
        return value
    text = _unquote(str(value).strip())
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def tokenize_info(value: str) -> list[str]:
    return [
        match.group(0)
        for match in re.finditer(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\S+', value)
    ]


def normalize_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized in {"py", "python3", "marimo"}:
        return "python"
    if normalized == "md":
        return "markdown"
    return normalized


def parse_attribute_tokens(tokens: list[str]) -> tuple[bool, CellOptions]:
    options: CellOptions = {}
    is_marimo = False

    for token in tokens:
        if token == ".marimo":
            is_marimo = True
            continue
        if token.startswith(".") or token.startswith("#"):
            continue
        if "=" not in token:
            options[token] = True
            continue
        key, value = token.split("=", 1)
        options[key] = parse_scalar(value)

    return is_marimo, options


def parse_code_meta(language: str, meta: str | None) -> CellOptions | None:
    language = normalize_language(language)
    if language not in {"python", "sql", "markdown"}:
        return None
    if not meta:
        return None

    text = meta.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    is_marimo, options = parse_attribute_tokens(tokenize_info(text[1:-1].strip()))
    if not is_marimo:
        return None
    options.pop("language", None)
    return {"language": language, **options}


def parse_braced_fence_info(info: str) -> CellOptions | None:
    text = info.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    tokens = tokenize_info(text[1:-1].strip())
    if not tokens:
        return None

    first, rest = tokens[0], tokens[1:]
    if first.endswith(".marimo"):
        language = first.removesuffix(".marimo")
        return parse_code_meta(language, "{" + " ".join([".marimo", *rest]) + "}")
    if first in {"python", "py", "python3", "sql", "markdown", "md", "marimo"}:
        return parse_code_meta(first, "{" + " ".join(rest) + "}")
    return None


def parse_plain_fence_info(info: str) -> CellOptions | None:
    if braced := parse_braced_fence_info(info):
        return braced
    match = re.fullmatch(r"(?P<language>\S+)\s+(?P<meta>\{.*\})", info.strip())
    if match is None:
        return None
    return parse_code_meta(match["language"], match["meta"])


def source_fences(source: str) -> list[SourceFence]:
    fences: list[SourceFence] = []
    lines = source.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(
            r"^(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$",
            line,
        )
        if match is None:
            index += 1
            continue

        fence = match["fence"]
        info = match["info"].strip()
        close_index = index + 1
        while close_index < len(lines):
            if re.match(
                rf"^[ \t]{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$",
                lines[close_index],
            ):
                break
            close_index += 1
        if close_index >= len(lines):
            break

        options = parse_plain_fence_info(info)
        if options is not None:
            body_lines = strip_fence_body_indent(
                lines[index + 1 : close_index],
                match["indent"],
            )
            fences.append(
                SourceFence(
                    start_line=index + 1,
                    language=str(options["language"]),
                    code="\n".join(body_lines),
                    options=options,
                )
            )
        index = close_index + 1
    return fences


def strip_fence_body_indent(lines: list[str], opening_indent: str) -> list[str]:
    """Mirror CommonMark's removal of the opening fence indentation."""
    max_spaces = opening_indent.count(" ")
    if max_spaces == 0:
        return lines

    stripped: list[str] = []
    for line in lines:
        spaces = len(line) - len(line.lstrip(" "))
        stripped.append(line[min(spaces, max_spaces) :])
    return stripped


def read_frontmatter(source: str) -> dict[str, Any]:
    match = FRONTMATTER_PATTERN.match(source)
    if match is None:
        return {}
    parsed = yaml.safe_load(match["body"]) or {}
    if not isinstance(parsed, dict):
        raise ValueError("YAML frontmatter must be a mapping")
    return parsed


def _frontmatter_string(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"frontmatter.options.marimo.{key} must be a string")
    return dedent(value).rstrip()


def metadata_from_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    options = frontmatter.get("options")
    if options is None:
        return {}
    if not isinstance(options, dict):
        raise ValueError("frontmatter.options must be a mapping")

    marimo = options.get("marimo")
    if marimo is None:
        return {}
    if not isinstance(marimo, dict):
        raise ValueError("frontmatter.options.marimo must be a mapping")

    metadata: dict[str, Any] = {}
    for key in ("header", "pyproject"):
        value = _frontmatter_string(marimo.get(key), key)
        if value is not None:
            metadata[key] = value
    for key in PAGE_EXECUTION_OPTION_KEYS:
        if key in marimo:
            metadata[key] = parse_scalar(marimo[key])
    return metadata


def source_page(source: str, path: Path | None = None) -> SourcePage:
    return SourcePage(
        metadata=metadata_from_frontmatter(read_frontmatter(source)),
        fences=source_fences(source),
        path=path,
    )


def code_cell_from_node(
    node: dict[str, Any], source_options: CellOptions | None = None
) -> Cell | None:
    if node.get("type") != "code":
        return None
    options = parse_code_meta(str(node.get("lang") or ""), node.get("meta"))
    if options is None:
        options = source_options
    if options is None:
        return None
    return Cell(
        code=str(node.get("value") or ""),
        options=options,
        position=node.get("position")
        if isinstance(node.get("position"), dict)
        else None,
    )
