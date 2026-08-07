from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Bundle the browser assets included in the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version, build_data
        subprocess.run(
            [sys.executable, "scripts/bundle_widget.py"],
            cwd=Path(self.root),
            check=True,
        )
