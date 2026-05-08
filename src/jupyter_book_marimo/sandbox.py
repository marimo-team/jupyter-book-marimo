"""Convert page-level dependency metadata into ``uv run`` arguments."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marimo._cli.sandbox import construct_uv_flags
    from marimo._utils.inline_script_metadata import PyProjectReader
else:
    try:
        from marimo._internal.sandbox import PyProjectReader, construct_uv_flags
    except ImportError:
        from marimo._cli.sandbox import construct_uv_flags
        from marimo._utils.inline_script_metadata import PyProjectReader


def uv_run_args(header: str) -> list[str]:
    """Build the ``uv run`` argument list for one document.

    The plugin passes dependency declarations as raw metadata text. We first
    wrap that in inline script metadata so dependency resolution follows
    marimo's existing sandbox rules instead of a second copy of the same logic
    here.
    """
    if not header.startswith("#"):
        header = "\n# ".join(["# /// script", *header.splitlines(), "///"])
    pyproject = PyProjectReader.from_script(header)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt"
    ) as temp_file:
        flags = construct_uv_flags(pyproject, temp_file, [], [])
        temp_file.flush()
    return ["run"] + flags  # type: ignore[no-any-return]
