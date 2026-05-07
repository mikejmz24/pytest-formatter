"""
pytest_glaze/_colors.py — ANSI color helpers and outcome tables.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
Call set_theme() to switch palettes. Color functions read _active_palette at
call time so all downstream rendering picks up the change immediately.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Dict

from pytest_glaze._types import Theme


def _should_disable_color() -> bool:
    """
    Single source of truth for color-mode evaluation.

    Currently called once at import time and cached in _NO_COLOR. Future
    versions may call this dynamically per render to support runtime
    color toggling, log redirection, and embedded use cases.
    """
    return not sys.stdout.isatty() or bool(os.environ.get("NO_COLOR"))


_NO_COLOR = _should_disable_color()

# ── Palettes ──────────────────────────────────────────────────────────────────

_DARK_PALETTE: Dict[str, str] = {
    "pass": "92",  # bright green
    "fail": "91",  # bright red
    "error": "31",  # standard red
    "skip": "93",  # bright yellow
    "xfail": "91",  # bright red
    "xpass": "93",  # bright yellow
    "emsg": "0;38;2;252;205;174",  # soft peach
    "section": "90",  # gray
    "dim": "2",
    "bold": "1",
    "bdd_feature": "0;38;2;220;248;255",  # baby blue
    "bdd_scenario": "0;38;2;170;225;255",  # steel blue
}

_LIGHT_PALETTE: Dict[str, str] = {
    "pass": "32",  # standard green
    "fail": "31",  # standard red
    "error": "0;38;2;160;0;0",  # dark red
    "skip": "33",  # amber
    "xfail": "31",  # standard red
    "xpass": "33",  # amber
    "emsg": "0;38;2;160;70;0",  # rust
    "section": "90",  # gray (unchanged)
    "dim": "2",
    "bold": "1",
    "bdd_feature": "34",  # dark blue
    "bdd_scenario": "0;38;2;0;100;190",  # medium blue
}

_active_palette: Dict[str, str] = _DARK_PALETTE

# ── Theme helpers ─────────────────────────────────────────────────────────────


def detect_theme() -> Theme:
    """
    Infer the terminal background theme from environment variables.

    Checks $COLORFGBG (set by xterm, iTerm2, most Linux terminals).
    Format: 'fg;bg' or 'fg;...;bg'. Background index >= 7 means light.

    Falls back to 'dark' — a safer default for unknown terminals.
    """
    colorfgbg = os.environ.get("COLORFGBG", "").strip()
    if colorfgbg:
        try:
            bg = int(colorfgbg.split(";")[-1])
            return "light" if bg >= 7 else "dark"
        except ValueError:
            pass
    return "dark"


def set_theme(theme: Theme) -> None:
    """
    Switch the active color palette.

    'auto' resolves to 'dark' or 'light' via detect_theme().
    Safe to call multiple times — last call wins.
    """
    global _active_palette  # pylint: disable=global-statement
    resolved = detect_theme() if theme == "auto" else theme
    _active_palette = _LIGHT_PALETTE if resolved == "light" else _DARK_PALETTE


def reset_theme() -> None:
    """Reset the active palette to the default (dark). For use in tests."""
    global _active_palette  # pylint: disable=global-statement
    _active_palette = _DARK_PALETTE


# ── Escape helper ─────────────────────────────────────────────────────────────


def _esc(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


# ── Color functions (read _active_palette at call time) ───────────────────────


def c_pass(t: str) -> str:
    """Green — passing tests / expected values."""
    return _esc(_active_palette["pass"], t)


def c_fail(t: str) -> str:
    """Red — FAIL badge, received values in assertions."""
    return _esc(_active_palette["fail"], t)


def c_error(t: str) -> str:
    """Red — ERROR badge, collection errors, setup/teardown crashes."""
    return _esc(_active_palette["error"], t)


def c_skip(t: str) -> str:
    """Yellow — skipped tests."""
    return _esc(_active_palette["skip"], t)


def c_xfail(t: str) -> str:
    """Red — expected failures."""
    return _esc(_active_palette["xfail"], t)


def c_xpass(t: str) -> str:
    """Yellow — unexpected passes."""
    return _esc(_active_palette["xpass"], t)


def c_emsg(t: str) -> str:
    """Peach / rust — E-line messages, context lines, assert keywords."""
    return _esc(_active_palette["emsg"], t)


def c_section(t: str) -> str:
    """Gray — captured output section headers."""
    return _esc(_active_palette["section"], t)


def c_dim(t: str) -> str:
    """Dim — metadata, timing."""
    return _esc(_active_palette["dim"], t)


def c_bold(t: str) -> str:
    """Bold — totals label."""
    return _esc(_active_palette["bold"], t)


def c_bdd_feature(t: str) -> str:
    """Blue — BDD Feature label."""
    return _esc(_active_palette["bdd_feature"], t)


def c_bdd_scenario(t: str) -> str:
    """Blue — BDD Scenario label."""
    return _esc(_active_palette["bdd_scenario"], t)


# ── Outcome tables ────────────────────────────────────────────────────────────

_OUTCOME_ORDER = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")

_BADGE_LABELS: Dict[str, str] = {
    "passed": "PASS",
    "failed": "FAIL",
    "error": "ERROR",
    "skipped": "SKIP",
    "xfailed": "XFAIL",
    "xpassed": "XPASS",
}

_OUTCOME_COLOR: Dict[str, Callable[[str], str]] = {
    "passed": c_pass,
    "failed": c_fail,
    "error": c_error,
    "skipped": c_skip,
    "xfailed": c_xfail,
    "xpassed": c_xpass,
}

_SUMMARY_FMT: Dict[str, Callable[[int], str]] = {
    "passed": lambda n: c_pass(f"{n} passed"),
    "failed": lambda n: c_fail(f"{n} failed"),
    "error": lambda n: c_error(f"{n} error" if n == 1 else f"{n} errors"),
    "skipped": lambda n: c_skip(f"{n} skipped"),
    "xfailed": lambda n: c_xfail(f"{n} xfailed"),
    "xpassed": lambda n: c_xpass(f"{n} xpassed"),
}


def get_badge(outcome: str) -> str:
    """Return a colored badge string for the given outcome."""
    label = _BADGE_LABELS.get(outcome, outcome.upper())
    color_fn = _OUTCOME_COLOR.get(outcome)
    return color_fn(label) if color_fn is not None else label


__all__ = [
    "_NO_COLOR",
    "_esc",
    "_DARK_PALETTE",
    "_LIGHT_PALETTE",
    "c_pass",
    "c_fail",
    "c_error",
    "c_skip",
    "c_xfail",
    "c_xpass",
    "c_emsg",
    "c_section",
    "c_dim",
    "c_bold",
    "c_bdd_feature",
    "c_bdd_scenario",
    "detect_theme",
    "set_theme",
    "reset_theme",
    "get_badge",
    "_BADGE_LABELS",
    "_OUTCOME_ORDER",
    "_OUTCOME_COLOR",
    "_SUMMARY_FMT",
]
