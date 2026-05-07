# tests/conftest.py
"""Shared test infrastructure for all pytest-glaze unit tests."""

import pytest

from pytest_glaze import _colors
from pytest_glaze._colors import reset_theme


@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output regardless of TTY detection."""
    monkeypatch.setattr(_colors, "_NO_COLOR", False)


@pytest.fixture(autouse=True)
def reset_palette():
    """Restore the default palette after each test to prevent state bleed."""
    yield
    reset_theme()
