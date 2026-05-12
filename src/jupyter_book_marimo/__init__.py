"""Executable MyST plugin for rendering marimo cells in Jupyter Book."""

from __future__ import annotations


def main() -> None:
    from .plugin import main as plugin_main

    plugin_main()


__all__ = ["main"]
