"""Run the Jupyter Book executable plugin command."""

from __future__ import annotations

from .plugin import main

if __name__ == "__main__":
    main()

__all__ = ["main"]
