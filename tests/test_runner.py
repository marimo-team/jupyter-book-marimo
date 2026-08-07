from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from helpers import cell, compiled_cell, compiled_page, request

from jupyter_book_marimo.runner import run_page_compiler, run_uv_compiler


def test_current_environment_uses_bounded_compiler_subprocess() -> None:
    expected = compiled_page(compiled_cell(0))
    page_request = request(cell(0))

    with patch(
        "jupyter_book_marimo.runner.run_compiler_process",
        return_value=expected,
    ) as run:
        actual = run_page_compiler(page_request)

    assert actual == expected
    assert run.call_args.args[1] == page_request


def test_external_environment_uses_compiler_subprocess() -> None:
    expected = compiled_page(compiled_cell(0))
    page_request = request(cell(0))

    with patch(
        "jupyter_book_marimo.runner.run_compiler_process",
        return_value=expected,
    ) as run:
        actual = run_page_compiler(page_request, external_env=True)

    assert actual == expected
    assert run.call_args.args[1] == page_request


def test_pyproject_uses_uv_compiler_environment() -> None:
    expected = compiled_page(compiled_cell(0))
    page_request = request(
        cell(0),
        pyproject='dependencies = ["typing-extensions"]',
    )

    with patch(
        "jupyter_book_marimo.runner.run_uv_compiler",
        return_value=expected,
    ) as run:
        actual = run_page_compiler(page_request)

    assert actual == expected
    run.assert_called_once_with(page_request)


def test_uv_compiler_uses_a_temporary_launcher_and_compiler_environment() -> None:
    expected = compiled_page(compiled_cell(0))
    page_request = request(
        cell(0),
        pyproject='dependencies = ["typing-extensions"]',
    )

    def inspect_compiler_call(
        command: list[str],
        actual_request: object,
        *,
        env: dict[str, str],
    ) -> object:
        assert Path(command[-1]).is_file()
        assert actual_request == page_request
        assert env == {"MARIMO_TEST": "1"}
        return expected

    with (
        patch("jupyter_book_marimo.runner.uv_command", return_value=["uv"]),
        patch(
            "jupyter_book_marimo.runner.compiler_environment",
            return_value=nullcontext({"MARIMO_TEST": "1"}),
        ),
        patch(
            "jupyter_book_marimo.runner.run_compiler_process",
            side_effect=inspect_compiler_call,
        ),
    ):
        actual = run_uv_compiler(page_request)

    assert actual == expected
