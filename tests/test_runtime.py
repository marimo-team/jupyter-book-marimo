from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from jupyter_book_marimo import runtime


@contextmanager
def fake_uv_run_args(_pyproject: str = "") -> Iterator[list[str]]:
    yield ["uv-run-args"]


def use_fake_uv(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "uv_run_args", fake_uv_run_args)
    monkeypatch.setattr(runtime, "uv_command", lambda: ["uv-command"])


def test_run_extractor_process_reports_timeout(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "UV_RUN_TIMEOUT_SECONDS", 7)

    def fake_run(command, **kwargs):
        assert kwargs["timeout"] == 7
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="timed out after 7s"):
        runtime.run_extractor_process(["uv", "run"], {"metadata": {}})


def test_pyproject_extractor_routes_through_uv(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, object], dict[str, str] | None]] = []

    def fake_process(command, payload, *, env=None):
        calls.append((command, payload, env))
        return {"outputs": []}

    monkeypatch.setattr(runtime, "run_extractor_process", fake_process)
    use_fake_uv(monkeypatch)
    payload = {"metadata": {"pyproject": "dependencies = []"}}

    assert runtime.run_extractor(payload) == {"outputs": []}
    _command, extracted_payload, env = calls[0]
    assert extracted_payload == payload
    assert env is not None


def test_uv_extractor_reports_invalid_json_output(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return SimpleNamespace(
            args=command,
            returncode=0,
            stdout="not json",
            stderr="warning before json",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    use_fake_uv(monkeypatch)

    with pytest.raises(RuntimeError, match="invalid JSON") as exc_info:
        runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}})

    message = str(exc_info.value)
    assert "warning before json" in message
    assert "not json" in message


def test_uv_extractor_returns_json_payload(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return SimpleNamespace(
            args=command,
            returncode=0,
            stdout=json.dumps({"outputs": []}),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    use_fake_uv(monkeypatch)

    assert runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}}) == {
        "outputs": []
    }


def test_pyproject_extractor_requires_uv(monkeypatch) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "uv", None)

    with pytest.raises(RuntimeError, match="uses uv"):
        runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}})


def test_pyproject_extractor_accepts_importable_uv_when_executable_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "uv", SimpleNamespace())
    monkeypatch.setattr(runtime, "uv_run_args", fake_uv_run_args)

    def fake_process(command, payload, *, env=None):
        assert payload == {"metadata": {"pyproject": "dependencies = []"}}
        assert env is not None
        return {"outputs": []}

    monkeypatch.setattr(runtime, "run_extractor_process", fake_process)

    assert runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}}) == {
        "outputs": []
    }


def test_default_extractor_runs_in_process_and_redirects_stdout(
    monkeypatch,
    capsys,
) -> None:
    initialized = False

    def fake_initialize() -> None:
        nonlocal initialized
        initialized = True

    async def fake_extract(payload):
        assert initialized
        assert payload == {"metadata": {}}
        print("cell stdout")
        return {"outputs": []}

    monkeypatch.setattr(runtime, "initialize_marimo_asyncio", fake_initialize)
    monkeypatch.setattr(runtime, "extract", fake_extract)

    assert runtime.run_extractor({"metadata": {}}) == {"outputs": []}
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "cell stdout\n"


def test_external_env_extractor_uses_current_interpreter(monkeypatch) -> None:
    payload = {"metadata": {"external_env": True}}
    calls: list[tuple[list[str], dict[str, object], dict[str, str] | None]] = []

    def fake_process(command, payload, *, env=None):
        calls.append((command, payload, env))
        return {"outputs": []}

    monkeypatch.setattr(runtime, "run_extractor_process", fake_process)

    assert runtime.run_extractor(payload) == {"outputs": []}
    _command, extracted_payload, env = calls[0]
    assert extracted_payload == payload
    assert env is not None


def test_extract_module_cli_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "jupyter_book_marimo.extract"],
        input=json.dumps(
            {
                "file": "docs/api/test.md",
                "metadata": {},
                "cells": [{"code": "1"}],
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["outputs"][0]["html"]


def assert_legal_future_imports(code: str, expected_names: set[str]) -> None:
    compile(code, "<exported notebook>", "exec")
    tree = ast.parse(code)
    top_level_nodes = {id(node) for node in tree.body}
    names: list[str] = []
    seen_non_future = False

    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            assert not seen_non_future
            names.extend(alias.name for alias in node.names)
        else:
            seen_non_future = True

    nested_future_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and id(node) not in top_level_nodes
    ]
    assert nested_future_imports == []
    assert set(names) == expected_names


def execute_notebook_code(code: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(code, namespace)
    return namespace


def test_hoist_future_imports_preserves_code_after_nested_imports() -> None:
    code = (
        "def f():\n"
        "    from __future__ import print_function\n"
        "    return 1\n"
        "from __future__ import annotations\n"
        "x = 1\n"
    )

    result = runtime.hoist_future_imports(code)

    assert_legal_future_imports(result, {"annotations", "print_function"})
    namespace = execute_notebook_code(result)
    assert namespace["f"]() == 1
    assert namespace["x"] == 1


def test_hoist_future_imports_preserves_code_after_multiple_nested_imports() -> None:
    code = (
        "def f():\n"
        "    from __future__ import annotations\n"
        "    return 1\n"
        "def g():\n"
        "    from __future__ import division\n"
        "    return 2\n"
        "x = 1\n"
    )

    result = runtime.hoist_future_imports(code)

    assert_legal_future_imports(result, {"annotations", "division"})
    namespace = execute_notebook_code(result)
    assert namespace["f"]() == 1
    assert namespace["g"]() == 2
    assert namespace["x"] == 1


def test_hoist_future_imports_dedents_parenthesized_imports() -> None:
    code = (
        "def f():\n"
        "    from __future__ import (\n"
        "        annotations,\n"
        "        division,\n"
        "    )\n"
        "    return 1\n"
        "x = 1\n"
    )

    result = runtime.hoist_future_imports(code)

    assert_legal_future_imports(result, {"annotations", "division"})
    namespace = execute_notebook_code(result)
    assert namespace["f"]() == 1
    assert namespace["x"] == 1


def test_hoist_future_imports_wraps_syntax_errors() -> None:
    with pytest.raises(RuntimeError, match="Could not parse exported notebook code"):
        runtime.hoist_future_imports("def f(:\n")
