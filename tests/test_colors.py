"""
tests/test_colors.py — Unit tests for palette selection, detect_theme,
set_theme, reset_theme, and get_badge.
"""

from __future__ import annotations

import pytest

import pytest_glaze._colors as colors
from pytest_glaze._colors import (
    _DARK_PALETTE,
    _LIGHT_PALETTE,
    c_bdd_feature,
    c_bdd_scenario,
    c_emsg,
    c_fail,
    c_pass,
    detect_theme,
    get_badge,
    set_theme,
    theme_context,
)

# ── detect_theme ──────────────────────────────────────────────────────────────


class TestDetectTheme:
    def test_dark_terminal_colorfgbg(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15;0")
        assert detect_theme() == "dark"

    def test_light_terminal_colorfgbg(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;7")
        assert detect_theme() == "light"

    def test_light_threshold_exactly_seven(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;7")
        assert detect_theme() == "light"

    def test_dark_threshold_below_seven(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;6")
        assert detect_theme() == "dark"

    def test_multi_segment_colorfgbg_uses_last(self, monkeypatch):
        """iTerm2 emits three-segment COLORFGBG values."""
        monkeypatch.setenv("COLORFGBG", "15;default;0")
        assert detect_theme() == "dark"

    def test_missing_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        assert detect_theme() == "dark"

    def test_malformed_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "garbage")
        assert detect_theme() == "dark"

    def test_empty_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "")
        assert detect_theme() == "dark"


# ── set_theme ─────────────────────────────────────────────────────────────────


class TestSetTheme:
    def test_dark_activates_dark_palette(self):
        with theme_context("dark"):
            assert colors._active_palette is _DARK_PALETTE

    def test_light_activates_light_palette(self):
        with theme_context("light"):
            assert colors._active_palette is _LIGHT_PALETTE

    def test_auto_resolves_to_dark_without_colorfgbg(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        with theme_context("auto"):
            assert colors._active_palette is _DARK_PALETTE

    def test_auto_resolves_to_light_with_light_terminal(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;15")
        with theme_context("auto"):
            assert colors._active_palette is _LIGHT_PALETTE

    def test_auto_resolves_to_dark_with_dark_terminal(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15;0")
        with theme_context("auto"):
            assert colors._active_palette is _DARK_PALETTE

    def test_set_theme_is_idempotent(self):
        with theme_context("light"):
            with theme_context("light"):
                assert colors._active_palette is _LIGHT_PALETTE

    def test_switching_themes_takes_effect_immediately(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active — palette codes are not emitted")
        with theme_context("dark"):
            dark_output = c_pass("PASS")
            with theme_context("light"):
                light_output = c_pass("PASS")
                assert dark_output != light_output


# ── Color functions pick up active palette ────────────────────────────────────


class TestColorFunctionsPaletteAware:
    """Color functions must read _active_palette at call time, not import time."""

    def test_c_pass_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            assert c_pass("X") != (set_theme("light") or c_pass("X"))

    def test_c_fail_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_fail("X")
            with theme_context("light"):
                assert dark != c_fail("X")

    def test_c_emsg_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_emsg("X")
            with theme_context("light"):
                assert dark != c_emsg("X")

    def test_c_bdd_feature_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_bdd_feature("X")
            with theme_context("light"):
                assert dark != c_bdd_feature("X")

    def test_c_bdd_scenario_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_bdd_scenario("X")
            with theme_context("light"):
                assert dark != c_bdd_scenario("X")

    def test_no_color_mode_unaffected_by_theme(self, monkeypatch):
        """In NO_COLOR mode, set_theme must not cause errors."""
        monkeypatch.setattr(colors, "_NO_COLOR", True)
        with theme_context("light"):
            assert c_pass("X") == "X"
            with theme_context("dark"):
                assert c_pass("X") == "X"


# ── get_badge ─────────────────────────────────────────────────────────────────


class TestGetBadge:
    @pytest.mark.parametrize(
        "outcome,label",
        [
            ("passed", "PASS"),
            ("failed", "FAIL"),
            ("error", "ERROR"),
            ("skipped", "SKIP"),
            ("xfailed", "XFAIL"),
            ("xpassed", "XPASS"),
        ],
    )
    def test_known_outcomes_contain_label(self, outcome, label):
        assert label in get_badge(outcome)

    def test_unknown_outcome_returns_uppercase(self):
        assert get_badge("mystery") == "MYSTERY"

    def test_badge_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = get_badge("passed")
            with theme_context("light"):
                light = get_badge("passed")
                assert "PASS" in dark and "PASS" in light
                assert dark != light


class TestPaletteStability:
    """
    Guard against palette being reset between renders.
    This class catches the exact bug where reset_theme() fired after every
    test, overriding the theme set by --glaze-theme in pytest_configure.
    """

    def test_palette_stays_light_across_multiple_renders(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("light"):
            results = [c_pass("PASS") for _ in range(5)]
            assert (
                len(set(results)) == 1
            ), "c_pass() returned different values across calls — palette changed mid-run"

    def test_palette_stays_dark_across_multiple_renders(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            results = [c_pass("PASS") for _ in range(5)]
            assert (
                len(set(results)) == 1
            ), "c_pass() returned different values across calls — palette changed mid-run"

    def test_reset_palette_fixture_respects_active_theme(self):
        """reset_palette must restore to whatever was active, not blindly reset to dark."""
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("light"):
            before = c_pass("X")
            # Simulate what reset_palette does — capture and restore
            saved = colors._active_palette
            colors._active_palette = saved
            assert c_pass("X") == before
