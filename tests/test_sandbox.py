from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from jupyter_book_marimo import runtime
from jupyter_book_marimo.runtime import sandbox_env, source_root, uv_run_args


def test_uv_run_args_runs_with_author_dependencies_and_marimo(tmp_path: Path) -> None:
    with (
        uv_run_args('# comment\ndependencies = ["packaging"]') as args,
        sandbox_env() as env,
    ):
        result = subprocess.run(
            [
                *runtime.uv_command(),
                *args,
                "python",
                "-c",
                "import jupyter_book_marimo, marimo, packaging",
            ],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )

    assert result.returncode == 0, result.stderr


def test_sandbox_env_imports_plugin_from_temporary_root() -> None:
    with sandbox_env() as env:
        pythonpath_values = env["PYTHONPATH"].split(os.pathsep)
        import_root = Path(pythonpath_values[0])
        pythonpath_entries = [Path(path).resolve() for path in pythonpath_values]
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import jupyter_book_marimo.extract as extract; "
                    "print(extract.__file__)"
                ),
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert Path(result.stdout.strip()).is_relative_to(import_root)
        assert source_root().resolve() not in pythonpath_entries

    assert not import_root.exists()


def test_sandbox_env_exposes_installed_package_version() -> None:
    with sandbox_env() as env:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from importlib.metadata import version; "
                    "import jupyter_book_marimo as jbm; "
                    "expected = version('jupyter-book-marimo'); "
                    "raise SystemExit(0 if jbm.__version__ == expected else 1)"
                ),
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr


def test_sandbox_env_preserves_existing_pythonpath(monkeypatch, tmp_path: Path) -> None:
    existing = tmp_path / "extra"
    existing.mkdir()
    monkeypatch.setenv("PYTHONPATH", str(existing))

    with sandbox_env() as env:
        paths = env["PYTHONPATH"].split(os.pathsep)
        assert Path(paths[0]).exists()
        assert paths[0] != str(existing)
        assert paths[1:] == [str(existing)]


def test_distinfo_scans_package_root_when_files_are_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    metadata_dir = tmp_path / "jupyter_book_marimo-1.2.3.dist-info"
    metadata_dir.mkdir()
    dist = SimpleNamespace(
        files=None,
        locate_file=lambda path: tmp_path / str(path),
        metadata={"Name": "jupyter-book-marimo"},
        version="1.2.3",
    )
    monkeypatch.setattr(runtime, "distribution", lambda name: dist)

    assert runtime.distinfo() == metadata_dir


def test_distinfo_ignores_similar_distinfo_names(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "jupyter_book_marimo_extra-9.9.9.dist-info").mkdir()
    metadata_dir = tmp_path / "jupyter_book_marimo-1.2.3.dist-info"
    metadata_dir.mkdir()
    dist = SimpleNamespace(
        files=None,
        locate_file=lambda path: tmp_path / str(path),
        metadata={"Name": "jupyter-book-marimo"},
        version="1.2.3",
    )
    monkeypatch.setattr(runtime, "distribution", lambda name: dist)

    assert runtime.distinfo() == metadata_dir
