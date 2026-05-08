"""Convert page-level dependency metadata into ``uv run`` arguments."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
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


@contextmanager
def uv_run_args(pyproject: str) -> Iterator[list[str]]:
    """Build the ``uv run`` argument list for one document.

    The plugin passes dependency declarations as raw pyproject text. We first
    wrap that in inline script metadata so dependency resolution follows
    marimo's existing sandbox rules instead of reimplementing them here.
    """
    if pyproject.lstrip().startswith("# /// script"):
        script_metadata = pyproject
    else:
        script_metadata = "\n# ".join(["# /// script", *pyproject.splitlines(), "///"])
    pyproject_reader = PyProjectReader.from_script(script_metadata)
    with tempfile.TemporaryDirectory(prefix="jupyter-book-marimo-") as temp_dir:
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=temp_dir, suffix=".txt"
        ) as temp_file:
            flags = construct_uv_flags(pyproject_reader, temp_file, [], [])
            temp_file.flush()
        yield ["run", *flags]  # type: ignore[misc]
