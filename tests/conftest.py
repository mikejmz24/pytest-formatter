# tests/conftest.py
"""Shared test infrastructure for all pytest-glaze unit tests."""

import pytest

from pytest_glaze import _colors
from pytest_glaze._colors import get_active_palette, set_active_palette


@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output regardless of TTY detection."""
    monkeypatch.setattr(_colors, "_NO_COLOR", False)


@pytest.fixture(scope="session", autouse=True)
def configured_palette():
    """Capture the palette configured at session start (respects --glaze-theme)."""
    return get_active_palette()


@pytest.fixture(autouse=True)
def restore_palette(request):
    """Restore the session-configured palette after each test to prevent state bleed."""
    saved = request.getfixturevalue("configured_palette")
    yield
    set_active_palette(saved)
