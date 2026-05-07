"""
tests/corpus/acceptance/test_theme_selection.py — Acceptance tests for
theme selection via --glaze-theme flag and $COLORFGBG auto-detection.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when

import pytest_glaze._colors as colors
from pytest_glaze._colors import _DARK_PALETTE, _LIGHT_PALETTE, set_theme

# ── Scenarios ─────────────────────────────────────────────────────────────────


@scenario(
    "features/theme_selection.feature",
    "Default theme auto-detects a dark terminal",
)
def test_auto_detects_dark(): ...


@scenario(
    "features/theme_selection.feature",
    "Default theme auto-detects a light terminal",
)
def test_auto_detects_light(): ...


@scenario(
    "features/theme_selection.feature",
    "User explicitly selects the dark theme",
)
def test_explicit_dark(): ...


@scenario(
    "features/theme_selection.feature",
    "User explicitly selects the light theme",
)
def test_explicit_light(): ...


@scenario(
    "features/theme_selection.feature",
    "Explicit flag overrides the terminal environment",
)
def test_flag_overrides_env(): ...


@scenario(
    "features/theme_selection.feature",
    "Unknown or malformed COLORFGBG falls back to dark",
)
def test_malformed_colorfgbg_dark(): ...


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def theme_context() -> dict:
    return {"theme_flag": "auto"}


# ── Given ─────────────────────────────────────────────────────────────────────


@given(parsers.parse('the environment variable COLORFGBG is set to "{value}"'))
def colorfgbg_set(monkeypatch, value: str) -> None:
    monkeypatch.setenv("COLORFGBG", value)


@given("the --glaze-theme flag is not provided", target_fixture="theme_context")
def no_theme_flag() -> dict:
    return {"theme_flag": "auto"}


@given(
    parsers.parse('the --glaze-theme flag is set to "{value}"'),
    target_fixture="theme_context",
)
def theme_flag_set(value: str) -> dict:
    return {"theme_flag": value}


# ── When ──────────────────────────────────────────────────────────────────────


@when("pytest-glaze is configured")
def glaze_configured(theme_context: dict) -> None:
    set_theme(theme_context["theme_flag"])


# ── Then ──────────────────────────────────────────────────────────────────────


@then("the dark color palette is active")
def dark_palette_active() -> None:
    assert colors._active_palette is _DARK_PALETTE  # pylint: disable=protected-access


@then("the light color palette is active")
def light_palette_active() -> None:
    assert colors._active_palette is _LIGHT_PALETTE  # pylint: disable=protected-access
