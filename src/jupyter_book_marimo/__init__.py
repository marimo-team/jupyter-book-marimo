"""Package entrypoint for the Jupyter Book executable plugin.

The package keeps imports cheap and exposes the console-script main function
lazily so discovery does not load the transform pipeline until needed.
"""

from __future__ import annotations


def main() -> None:
    from .plugin import main as plugin_main

    plugin_main()


__all__ = ["main"]
