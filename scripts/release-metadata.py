"""Read the package version without installing the project."""

import json
import subprocess

version = subprocess.check_output(
    ["uv", "version", "--package", "jupyter-book-marimo", "--frozen", "--short"],
    text=True,
).strip()
print(json.dumps({"version": version}))
