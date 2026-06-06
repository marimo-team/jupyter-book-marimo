"""Convert rendered marimo islands into anywidget model payloads.

The extractor receives HTML from marimo. Hydration payloads, hidden cells, source
visibility, and MIME suppression share one output model shape.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
import html
import re

from .authoring import as_bool

ERROR_MIMETYPES = {
    "application/vnd.marimo+error",
    "application/vnd.marimo+traceback",
}


class AttributeParser(HTMLParser):
    """Collect attributes from one rendered HTML tag."""

    def __init__(self) -> None:
        super().__init__()
        self.attrs: dict[str, str] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.attrs = {key: value or "" for key, value in attrs}


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
    """Rewrite server cell IDs to browser-local cell indexes."""
    return re.sub(
        r'\s+data-cell-id="[^"]+"',
        f'\n    data-cell-idx="{cell_index}"',
        island,
        count=1,
    )


def hide_island_output(island: str) -> str:
    """Keep an island reactive while hiding its hydrated output."""
    return re.sub(
        r"(<marimo-island\b)",
        r'\1 data-jupyter-book-marimo-hide-output="true"',
        island,
        count=1,
    )


def hide_island(island: str) -> str:
    """Keep a reactive cell in DOM order while hiding the whole island."""
    return re.sub(
        r"(<marimo-island\b)",
        r'\1 hidden data-jupyter-book-marimo-hidden-cell="true"',
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
    runtime_cell_count: int | None = None,
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
    if runtime_cell_count is not None:
        model["runtimeCellCount"] = runtime_cell_count
    return model


def hidden_runtime_output(
    stub: Any,
    cell_index: int,
    app_id: str,
    *,
    html_prefix: str = "",
) -> dict[str, Any]:
    return output_model(
        html_prefix
        + hide_island(
            use_browser_cell_index(stub.render(display_output=False), cell_index)
        ),
        app_id=app_id,
    )


def widget_config_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {"molab": {"enabled": as_bool(metadata.get("molab"), default=True)}}


def normalized_mimetype(value: str) -> str:
    """Normalize escaped MIME attributes before option matching."""
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
