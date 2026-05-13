from __future__ import annotations

from jupyter_book_marimo.authoring import (
    DEFAULT_EXECUTION_OPTIONS,
    resolved_execution_options,
    should_display_code,
    should_display_output,
    should_execute,
    should_include,
)


def test_default_execution_option_vocabulary_is_implemented_public_api() -> None:
    assert tuple(DEFAULT_EXECUTION_OPTIONS) == (
        "eval",
        "echo",
        "output",
        "error",
        "include",
        "editor",
    )


def test_cell_execution_options_override_document_options() -> None:
    config = resolved_execution_options(
        {"eval": False, "echo": True},
        {"eval": True, "hide_code": True},
    )

    assert config["eval"] is True
    assert config["echo"] is True
    assert config["hide_code"] is True


def test_include_controls_rendering_not_execution() -> None:
    config = resolved_execution_options({}, {"include": False})

    assert should_include(config) is False
    assert should_execute(config) is True
    assert should_display_code(config) is False
    assert should_display_output(config) is False


def test_disabled_and_unparseable_skip_execution() -> None:
    assert should_execute(resolved_execution_options({}, {"disabled": True})) is False
    assert (
        should_execute(resolved_execution_options({}, {"unparseable": True})) is False
    )


def test_echo_and_editor_are_visible_code_requests() -> None:
    assert should_display_code(resolved_execution_options({}, {"echo": True})) is True
    assert should_display_code(resolved_execution_options({}, {"editor": True})) is True
    assert (
        should_display_code(
            resolved_execution_options({}, {"echo": True, "hide-code": True})
        )
        is False
    )
