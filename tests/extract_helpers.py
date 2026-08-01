from __future__ import annotations

import ast
import asyncio
import json
import warnings
from html.parser import HTMLParser
from typing import Any

from jupyter_book_marimo import extract
from jupyter_book_marimo.cell_plan import CellPlan


class MarimoCellOutputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.outputs: list[str] = []
        self._depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag == "marimo-cell-output":
            if self._depth > 0:
                self._chunks.append(self.get_starttag_text() or f"<{tag}>")
            self._depth += 1
            return
        if self._depth > 0:
            self._chunks.append(self.get_starttag_text() or f"<{tag}>")

    def handle_startendtag(
        self,
        tag: str,
        _attrs: list[tuple[str, str | None]],
    ) -> None:
        if self._depth > 0:
            self._chunks.append(self.get_starttag_text() or f"<{tag}/>")

    def handle_endtag(self, tag: str) -> None:
        if self._depth == 0:
            return
        if tag == "marimo-cell-output":
            self._depth -= 1
            if self._depth == 0:
                self.outputs.append("".join(self._chunks))
                self._chunks = []
                return
        self._chunks.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self._chunks.append(data)


class MarimoIslandParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attrs: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "marimo-island":
            self.attrs.append(dict(attrs))


def marimo_island_attrs(html: str) -> list[dict[str, str | None]]:
    parser = MarimoIslandParser()
    parser.feed(html)
    return parser.attrs


def single_marimo_island_attrs(html: str) -> dict[str, str | None]:
    attrs = marimo_island_attrs(html)
    assert len(attrs) == 1
    return attrs[0]


def marimo_island_indices(html: str) -> list[str]:
    return [
        str(attrs["data-cell-idx"])
        for attrs in marimo_island_attrs(html)
        if "data-cell-idx" in attrs
    ]


def marimo_cell_output_html(html: str) -> str:
    parser = MarimoCellOutputParser()
    parser.feed(html)
    assert len(parser.outputs) == 1
    return parser.outputs[0]


def marimo_cell_output_htmls(html: str) -> list[str]:
    parser = MarimoCellOutputParser()
    parser.feed(html)
    return parser.outputs


class HtmlSummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag != "marimo-mime-renderer":
            return
        values = {key: value or "" for key, value in attrs}
        data = values.get("data-data")
        if not data:
            return
        payload = json.loads(data)
        if not isinstance(payload, str):
            self._chunks.append(str(payload))
            return
        nested = HtmlSummaryParser()
        nested.feed(payload)
        self.tags.extend(nested.tags)
        self._chunks.extend(nested._chunks)

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self._chunks).split())


def html_summary(html: str) -> tuple[str, list[str]]:
    parser = HtmlSummaryParser()
    parser.feed(html)
    return parser.text, parser.tags


def marimo_cell_output_text(html: str) -> str:
    texts = [text for text in marimo_cell_output_texts(html) if text]
    assert len(texts) == 1
    return texts[0]


def marimo_cell_output_texts(html: str) -> list[str]:
    return [html_summary(output)[0] for output in marimo_cell_output_htmls(html)]


def marimo_cell_output_tags(html: str) -> list[str]:
    tags: list[str] = []
    for output in marimo_cell_output_htmls(html):
        _text, output_tags = html_summary(output)
        tags.extend(output_tags)
    return tags


class MimePayloadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.mimetypes: list[str] = []
        self.payloads: list[Any] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "marimo-mime-renderer":
            return
        values = {key: value or "" for key, value in attrs}
        mime = values.get("data-mime")
        if mime:
            self.mimetypes.append(json.loads(mime))
        data = values.get("data-data")
        if data:
            self.payloads.append(json.loads(data))


def marimo_mimetypes(html: str) -> list[str]:
    parser = MimePayloadParser()
    parser.feed(html)
    return parser.mimetypes


def marimo_mime_payloads(html: str) -> list[Any]:
    parser = MimePayloadParser()
    parser.feed(html)
    return parser.payloads


class CodeBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[tuple[str, str]] = []
        self._language = ""
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "code" or self._language:
            return
        values = {key: value or "" for key, value in attrs}
        language = next(
            (
                value.removeprefix("language-")
                for value in values.get("class", "").split()
                if value.startswith("language-")
            ),
            "",
        )
        self._language = language
        self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._language:
            self.blocks.append((self._language, "".join(self._chunks)))
            self._language = ""
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._language:
            self._chunks.append(data)


def code_blocks(html: str) -> list[tuple[str, str]]:
    parser = CodeBlockParser()
    parser.feed(html)
    return parser.blocks


class CodeEditorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "marimo-code-editor":
            return
        values = {key: value or "" for key, value in attrs}
        value = values.get("data-initial-value")
        if value is not None:
            self.values.append(json.loads(value))


def code_editor_values(html: str) -> list[str]:
    parser = CodeEditorParser()
    parser.feed(html)
    return parser.values


def assignment_values(source: str, name: str) -> list[object]:
    values: list[object] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if not isinstance(value, ast.Constant):
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                values.append(value.value)
    return values


def future_import_names(source: str) -> set[str]:
    compile(source, "<exported notebook>", "exec")
    tree = ast.parse(source)
    top_level_nodes = {id(node) for node in tree.body}
    names: list[str] = []
    seen_non_future = False

    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            assert not seen_non_future
            names.extend(alias.name for alias in node.names)
        else:
            seen_non_future = True

    nested_future_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and id(node) not in top_level_nodes
    ]
    assert nested_future_imports == []
    return set(names)


def markdown_cell_literals(source: str) -> list[str]:
    literals: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "md":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "mo":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        value = node.args[0].value
        if isinstance(value, str):
            literals.append(value)
    return literals


def cell_plan(
    code: str,
    *,
    options: dict[str, object] | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> CellPlan:
    payload: dict[str, object] = {
        "code": code,
        "options": {"language": "python", **(options or {})},
    }
    if start_line is not None:
        payload["startLine"] = start_line
    if end_line is not None:
        payload["endLine"] = end_line
    return CellPlan.from_payload(0, payload, {})


def run_extract(payload: dict[str, Any]) -> dict[str, Any]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        return asyncio.run(extract.extract(payload))
