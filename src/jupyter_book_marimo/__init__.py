"""Expose package metadata without importing the plugin pipeline."""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("jupyter-book-marimo")

__all__ = ["__version__"]
