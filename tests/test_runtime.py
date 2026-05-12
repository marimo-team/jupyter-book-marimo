from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from jupyter_book_marimo import runtime


def test_sandboxed_extractor_times_out(monkeypatch) -> None:
    @contextmanager
    def fake_uv_run_args(_pyproject: str) -> Iterator[list[str]]:
        yield ["run", "--with-requirements", "requirements.txt"]

    def fake_run(command, **kwargs):
        assert kwargs["timeout"] == runtime.UV_RUN_TIMEOUT_SECONDS
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runtime, "uv_run_args", fake_uv_run_args)
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="timed out after"):
        runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}})


def test_sandboxed_extractor_reports_invalid_json_output(monkeypatch) -> None:
    @contextmanager
    def fake_uv_run_args(_pyproject: str) -> Iterator[list[str]]:
        yield ["run", "--with-requirements", "requirements.txt"]

    def fake_run(command, **kwargs):
        return SimpleNamespace(
            args=command,
            returncode=0,
            stdout="not json",
            stderr="warning before json",
        )

    monkeypatch.setattr(runtime, "uv_run_args", fake_uv_run_args)
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="invalid JSON") as exc_info:
        runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}})

    message = str(exc_info.value)
    assert "warning before json" in message
    assert "not json" in message


def test_sandboxed_extractor_returns_json_payload(monkeypatch) -> None:
    @contextmanager
    def fake_uv_run_args(_pyproject: str) -> Iterator[list[str]]:
        yield ["run", "--with-requirements", "requirements.txt"]

    def fake_run(command, **kwargs):
        return SimpleNamespace(
            args=command,
            returncode=0,
            stdout=json.dumps({"outputs": []}),
            stderr="",
        )

    monkeypatch.setattr(runtime, "uv_run_args", fake_uv_run_args)
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert runtime.run_extractor({"metadata": {"pyproject": "dependencies = []"}}) == {
        "outputs": []
    }


def test_in_process_extractor_keeps_stdout_available_for_plugin_protocol(
    monkeypatch, capsys
) -> None:
    async def fake_extract(_payload):
        print("user stdout")
        return {"outputs": []}

    monkeypatch.setattr(runtime, "extract", fake_extract)

    assert runtime.run_extractor({"metadata": {}}) == {"outputs": []}
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "user stdout" in captured.err
