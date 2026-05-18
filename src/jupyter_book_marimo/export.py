# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "marimo>=0.23.5",
# ]
# ///
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from marimo._convert.converters import MarimoConvert
from marimo._utils import yaml

MARIMO_VERSION_KEY = "marimo-version"
CONFIG_KEYS = {"header", "pyproject"}
MARIMO_METADATA_KEYS = {MARIMO_VERSION_KEY, "width"}
SUPPORTED_SUFFIXES = {".py", ".md", ".markdown", ".qmd"}
FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<body>.*?\n?)(?:---)\s*(?:\n|$)",
    re.DOTALL,
)
SCRIPT_METADATA_RE = re.compile(
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s"
    r"(?P<content>(^#(| .*)$\s)+)^# ///$"
)
FENCE_START_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})(?P<info>.*)$")


def notebook_to_marimo_markdown(path: Path) -> str:
    # Match `marimo export md` first; the MyST pass only changes the authoring
    # surface, not how marimo parses Python or markdown notebooks.
    source = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".py":
        return MarimoConvert.from_py(source).to_markdown(path.name)
    if suffix in {".md", ".markdown", ".qmd"}:
        return MarimoConvert.from_md(source).to_markdown(path.name)
    expected = ", ".join(sorted(SUPPORTED_SUFFIXES))
    raise ValueError(f"Unsupported notebook suffix {suffix!r}; expected {expected}")


def split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(markdown)
    if match is None:
        return {}, markdown

    metadata = yaml.load(match.group("body"))
    return metadata, markdown[match.end() :]


def uncomment_script_metadata(content: str) -> str:
    return "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in content.splitlines(keepends=True)
    )


def split_script_metadata(header: str) -> tuple[str, str]:
    # Python notebooks expose PEP 723 as header comments after markdown export.
    # The book plugin expects dependencies in `marimo-config` instead.
    pyproject = ""

    def replace(match: re.Match[str]) -> str:
        nonlocal pyproject
        if match.group("type") != "script":
            return match.group(0)
        if not pyproject:
            pyproject = uncomment_script_metadata(match.group("content")).strip()
        return ""

    cleaned = SCRIPT_METADATA_RE.sub(replace, header).strip()
    return cleaned, pyproject


def myst_frontmatter(metadata: dict[str, Any]) -> str:
    metadata = {
        key: value
        for key, value in metadata.items()
        if key not in CONFIG_KEYS and key not in MARIMO_METADATA_KEYS
    }
    if not metadata:
        return ""
    body = yaml.marimo_compat_dump(metadata, sort_keys=False).strip()
    return "\n".join(
        [
            "---",
            body,
            "---",
            "",
            "",
        ]
    )


def myst_config(metadata: dict[str, Any]) -> str:
    header = str(metadata.get("header") or "").strip()
    header, header_pyproject = split_script_metadata(header)
    pyproject = str(metadata.get("pyproject") or header_pyproject).strip()

    config = {
        key: value
        for key, value in {"header": header, "pyproject": pyproject}.items()
        if value
    }
    if not config:
        return ""

    body = yaml.marimo_compat_dump(config, sort_keys=False).strip()
    return "\n".join(
        [
            "```{marimo-config}",
            "---",
            body,
            "---",
            "```",
            "",
            "",
        ]
    )


def parse_marimo_info(info: str) -> tuple[str, dict[str, str]] | None:
    # marimo markdown fences use attributes like `python {.marimo hide_code="true"}`;
    # MyST directives represent the same cell as ```{marimo} python + options.
    info = info.strip()
    match = re.match(r"^(?P<prefix>.*?)\s*\{(?P<attrs>[^}]*)\}\s*$", info)
    if match is None or "marimo" not in match.group("attrs"):
        return None

    prefix = match.group("prefix").strip()
    attrs = match.group("attrs").strip()
    language = prefix or "python"
    options: dict[str, str] = {}

    for token in shlex.split(attrs):
        if token.startswith("."):
            for marker in token.lstrip(".").split("."):
                if marker in {"python", "sql", "markdown"}:
                    language = marker
            continue
        if token == "marimo":
            continue
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.replace("_", "-")
        if key == "unparsable":
            key = "unparseable"
        if key == "language":
            language = value
        else:
            options[key] = value

    return language, options


def closing_fence(line: str, opening: str) -> bool:
    stripped = line.strip()
    return (
        bool(stripped)
        and set(stripped) == {opening[0]}
        and len(stripped) >= len(opening)
    )


def myst_directive(
    fence: str,
    language: str,
    options: dict[str, str],
    code_lines: list[str],
) -> str:
    # MyST executable directives require a body. marimo notebooks can contain
    # empty cells, so emit a no-op body with the same visible cell boundary.
    if not any(line.strip() for line in code_lines):
        code_lines = ["pass" if language == "python" else "-- empty cell"]

    lines = [f"{fence}{{marimo}} {language}"]
    for key, value in options.items():
        lines.append(f":{key}: {value}")
    if options:
        lines.append("")
    lines.extend(code_lines)
    lines.append(fence)
    return "\n".join(lines)


def rewrite_marimo_fences(markdown: str) -> str:
    # Walk fences explicitly so literal examples nested inside larger markdown
    # fences stay untouched while top-level executable marimo cells are rewritten.
    lines = markdown.splitlines()
    rewritten: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        match = FENCE_START_RE.match(line)
        if match is None:
            rewritten.append(line)
            index += 1
            continue

        fence = match.group("fence")
        parsed = parse_marimo_info(match.group("info"))
        if parsed is None:
            rewritten.append(line)
            index += 1
            while index < len(lines):
                rewritten.append(lines[index])
                if closing_fence(lines[index], fence):
                    index += 1
                    break
                index += 1
            continue

        language, options = parsed
        index += 1
        code_lines: list[str] = []
        while index < len(lines) and not closing_fence(lines[index], fence):
            code_lines.append(lines[index])
            index += 1
        if index == len(lines):
            rewritten.append(line)
            rewritten.extend(code_lines)
            continue
        rewritten.append(myst_directive(fence, language, options, code_lines))
        index += 1

    return "\n".join(rewritten).strip()


def export_myst(path: Path) -> str:
    markdown = notebook_to_marimo_markdown(path)
    metadata, body = split_frontmatter(markdown)
    return (
        myst_frontmatter(metadata)
        + myst_config(metadata)
        + rewrite_marimo_fences(body)
        + "\n"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a marimo notebook to MyST markdown for jupyter-book-marimo."
    )
    parser.add_argument("notebook", type=Path)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file. If omitted, writes to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        markdown = export_myst(args.notebook)
    except Exception as error:
        print(f"export.py: {error}", file=sys.stderr)
        return 1

    if args.output is None:
        print(markdown, end="")
    else:
        args.output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
