from __future__ import annotations

import email
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import zipfile

from marimo._utils.toml import toml_reader


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGE_NAME = "jupyter-book-marimo"


def smoke_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed\n{result.stderr}\n{result.stdout}".strip()
        )
    return result


def project_version() -> str:
    project = toml_reader.read(ROOT / "pyproject.toml")["project"]
    version = project["version"]
    if not isinstance(version, str):
        raise RuntimeError("Could not read project version from pyproject.toml")
    return version


def artifacts(version: str | None = None) -> list[Path]:
    version = version or project_version()
    artifact_set = sorted(path for path in DIST.iterdir() if path.name != ".gitignore")
    wheels = [path for path in artifact_set if path.suffix == ".whl"]
    sdists = [path for path in artifact_set if path.name.endswith(".tar.gz")]
    expected_paths = {*wheels, *sdists}
    unexpected = [path for path in artifact_set if path not in expected_paths]
    if len(wheels) != 1 or len(sdists) != 1 or unexpected:
        raise RuntimeError(
            "dist/ must contain exactly one wheel and one sdist; found "
            + ", ".join(str(path.relative_to(ROOT)) for path in artifact_set)
        )
    paths = [wheels[0], sdists[0]]
    assert_artifact_metadata(paths, version)
    return paths


def wheel_metadata(wheel: Path) -> email.message.Message:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        return email.message_from_bytes(archive.read(metadata_name))


def sdist_metadata(sdist: Path) -> email.message.Message:
    with tarfile.open(sdist, "r:gz") as archive:
        pkg_info = next(
            member
            for member in archive.getmembers()
            if member.name.endswith("/PKG-INFO")
        )
        extracted = archive.extractfile(pkg_info)
        if extracted is None:
            raise RuntimeError(f"Could not read {pkg_info.name}")
        return email.message_from_bytes(extracted.read())


def assert_artifact_metadata(paths: list[Path], expected_version: str) -> None:
    metadata = {
        path: wheel_metadata(path) if path.suffix == ".whl" else sdist_metadata(path)
        for path in paths
    }
    mismatches = {
        path: (str(values["Name"]), str(values["Version"]))
        for path, values in metadata.items()
        if values["Name"] != PACKAGE_NAME or values["Version"] != expected_version
    }
    if mismatches:
        details = ", ".join(
            f"{path.relative_to(ROOT)} has {name} {version}"
            for path, (name, version) in mismatches.items()
        )
        raise RuntimeError(
            f"Package artifact metadata mismatch: expected {PACKAGE_NAME} "
            f"{expected_version}; {details}"
        )


def plugin_spec(stdout: str) -> dict[str, object]:
    spec = json.loads(stdout)
    directives = {item["name"]: item for item in spec["directives"]}
    expected_directives = {"marimo", "marimo-config"}
    if set(directives) != expected_directives:
        raise RuntimeError(f"Unexpected directives: {set(directives)}")
    transforms = spec["transforms"]
    if not isinstance(transforms, list) or len(transforms) != 1:
        raise RuntimeError(f"Unexpected transforms: {transforms}")
    transform = transforms[0]
    if transform["name"] != "marimo-islands" or transform["stage"] != "document":
        raise RuntimeError(f"Unexpected transform contract: {transform}")
    if not isinstance(transform["doc"], str) or not transform["doc"]:
        raise RuntimeError(f"Unexpected transform doc: {transform}")
    return spec


def assert_matching_plugin_specs(*stdouts: str) -> None:
    specs = [plugin_spec(stdout) for stdout in stdouts]
    if any(spec != specs[0] for spec in specs[1:]):
        raise RuntimeError("Installed console script and package module disagree")


def smoke_artifact(artifact: Path) -> None:
    with TemporaryDirectory(prefix="jupyter-book-marimo-smoke-") as tmp:
        root = Path(tmp)
        venv = root / ".venv"
        env = smoke_env()
        run(["uv", "venv", "--python", sys.executable, str(venv)], cwd=root, env=env)
        python = venv / "bin" / "python"
        console_script = venv / "bin" / "jupyter-book-marimo"
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                str(artifact),
            ],
            cwd=root,
            env=env,
        )

        assert_matching_plugin_specs(
            run([str(console_script)], cwd=root, env=env).stdout,
            run([str(python), "-m", "jupyter_book_marimo"], cwd=root, env=env).stdout,
        )
        run(
            [
                str(python),
                "-c",
                (
                    "from importlib.metadata import version\n"
                    "from importlib.resources import files\n"
                    "import os\n"
                    "from pathlib import Path\n"
                    "from tempfile import TemporaryDirectory\n"
                    "import jupyter_book_marimo as jbm\n"
                    "from jupyter_book_marimo.plugin import widget_esm\n"
                    "if not Path(jbm.__file__).is_relative_to(Path.cwd() / '.venv'):\n"
                    "    raise RuntimeError(jbm.__file__)\n"
                    "if jbm.__version__ != version('jupyter-book-marimo'):\n"
                    "    raise RuntimeError(jbm.__version__)\n"
                    "asset = files('jupyter_book_marimo.assets').joinpath('container-widget.mjs')\n"
                    "packaged = asset.read_bytes()\n"
                    "if not packaged:\n"
                    "    raise RuntimeError('empty packaged widget asset')\n"
                    "with TemporaryDirectory() as tmpdir:\n"
                    "    os.chdir(tmpdir)\n"
                    "    if widget_esm() != '/.jupyter-book-marimo/container-widget.mjs':\n"
                    "        raise RuntimeError('unexpected widget ESM path')\n"
                    "    copied = Path('.jupyter-book-marimo/container-widget.mjs')\n"
                    "    if copied.read_bytes() != packaged:\n"
                    "        raise RuntimeError('copied widget asset differs')\n"
                ),
            ],
            cwd=root,
            env=env,
        )


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--check-artifacts-only":
        if len(args) > 2:
            raise RuntimeError(f"Unknown arguments: {' '.join(args)}")
        artifacts(args[1] if len(args) == 2 else None)
        return 0
    if args:
        raise RuntimeError(f"Unknown arguments: {' '.join(args)}")
    paths = artifacts()
    for artifact in paths:
        smoke_artifact(artifact)
        print(f"smoked {artifact.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())
