from __future__ import annotations

from pathlib import Path

from jupyter_book_marimo.runtime import uv_run_args


def test_uv_run_args_removes_temporary_requirements_file() -> None:
    with uv_run_args('dependencies = ["marimo>=0.23.5"]') as args:
        requirements_path = Path(args[args.index("--with-requirements") + 1])
        assert requirements_path.exists()

    assert not requirements_path.exists()


def test_uv_run_args_wraps_pyproject_that_starts_with_comment() -> None:
    with uv_run_args('# comment\ndependencies = ["marimo>=0.23.5"]') as args:
        requirements_path = Path(args[args.index("--with-requirements") + 1])
        assert "marimo" in requirements_path.read_text()
