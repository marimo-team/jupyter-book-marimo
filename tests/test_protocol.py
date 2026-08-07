from __future__ import annotations

import pytest

from jupyter_book_marimo.protocol import (
    CompiledMarimoPage,
    MarimoPageRequest,
)

from helpers import cell, compiled_cell, compiled_page, request


def test_page_request_round_trips_through_protocol_v2() -> None:
    page_request = request(cell(0, "x = 1"), identity="source:abc")
    payload = page_request.to_json()

    assert payload["protocolVersion"] == 2
    assert MarimoPageRequest.from_json(payload) == page_request


def test_compiled_output_round_trips_with_its_mime_type() -> None:
    page = compiled_page(compiled_cell(0))
    payload = page.to_json()

    assert payload["cells"][0]["output"]["mimetype"] == "text/plain"
    assert CompiledMarimoPage.from_json(payload) == page


def test_protocol_rejects_other_versions() -> None:
    payload = request(cell(0)).to_json()
    payload["protocolVersion"] = 1

    with pytest.raises(ValueError, match="unsupported marimo page protocol"):
        MarimoPageRequest.from_json(payload)


def test_compiled_cell_requires_output() -> None:
    payload = compiled_cell(0).to_json()
    del payload["output"]

    with pytest.raises(TypeError, match="compiled marimo cell output is required"):
        CompiledMarimoPage.from_json(
            {
                **compiled_page(compiled_cell(0)).to_json(),
                "cells": [payload],
            }
        )
