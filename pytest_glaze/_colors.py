"""
pytest_glaze/_colors.py — ANSI color helpers and outcome tables.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
Call set_theme() to switch palettes. Color functions read _active_palette at
call time so all downstream rendering picks up the change immediately.
"""

from __future__ import annotations

import ctypes as _ctypes
import os
import re
import select
import sys
import termios
import tty
from contextlib import contextmanager
from typing import Callable, Dict, Optional

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
    "pass": "0;38;2;0;120;0",  # dark forest green
    "fail": "0;38;2;200;0;0",  # deep red
    "error": "0;38;2;170;0;0",  # dark red
    "skip": "0;38;2;160;90;0",  # dark burnt amber
    "xfail": "0;38;2;200;0;0",  # deep red
    "xpass": "0;38;2;160;90;0",  # dark burnt amber
    "emsg": "0;38;2;80;0;160",  # dark violet
    "section": "0;38;2;80;80;80",  # dark gray
    "dim": "2",
    "bold": "1",
    "bdd_feature": "0;38;2;0;50;160",  # deep navy
    "bdd_scenario": "0;38;2;0;80;170",  # deep ocean blue
}

_active_palette: Dict[str, str] = _DARK_PALETTE

# ── Theme helpers ─────────────────────────────────────────────────────────────


def _osc11_safe_to_query() -> bool:
    """
    Return True only when an OSC 11 terminal query is safe to attempt.

    Checks all conditions that would make the query unsafe or pointless:
      - Windows: handled separately via ctypes
      - $TMUX set: tmux intercepts but does not forward OSC 11
      - $TERM starts with 'screen': screen multiplexer, same issue as tmux
      - /dev/tty not openable: headless CI, Docker, no controlling terminal
    """
    platform = sys.platform  # indirection avoids static-evaluation warning
    if platform == "win32":
        return False
    if bool(os.environ.get("TMUX")) or os.environ.get("TERM", "").startswith("screen"):
        return False
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        os.close(fd)
        return True
    except OSError:
        return False


def _query_osc11(timeout: float = 0.1) -> Optional[str]:
    """
    Query the terminal background color via OSC 11 escape sequence.

    OSC 11 is the standard xterm protocol for querying the terminal background
    color. We open ``/dev/tty`` directly — this gives us access to the actual
    terminal even when stdin/stdout are piped (e.g. through make, CI scripts,
    or output redirection). This is the same approach used by bat, fzf, and
    other terminal-aware tools.

    We write ``\\033]11;?\\033\\\\`` and read the ``rgb:RRRR/GGGG/BBBB`` response.

    Safety gates — returns None immediately if any of these are true:
      - ``/dev/tty`` cannot be opened (non-interactive, headless CI)
      - Platform is Windows (handled separately via ctypes)
      - $TMUX is set (tmux does not support OSC 11)
      - $TERM starts with "screen" (screen multiplexer, same issue)
      - Response is pure black rgb:0000/0000/0000 (buggy terminals like
        zellij and tabby always report black regardless of actual theme)

    Returns the raw rgb string (e.g. ``'rgb:ffff/ffff/ffff'``) or None if
    the query failed, timed out, or was skipped for safety.
    """

    if not _osc11_safe_to_query():
        return None

    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return None

    try:
        old_settings = termios.tcgetattr(tty_fd)
        try:
            tty.setraw(tty_fd)
            os.write(tty_fd, b"\033]11;?\033\\")
            ready, _, _ = select.select([tty_fd], [], [], timeout)
            if not ready:
                return None
            response = b""
            while True:
                ready, _, _ = select.select([tty_fd], [], [], 0.05)
                if not ready:
                    break
                chunk = os.read(tty_fd, 64)
                if not chunk:
                    break
                response += chunk
                if response.endswith(b"\033\\") or response.endswith(b"\007"):
                    break
        finally:
            termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_settings)
    except Exception:  # pylint: disable=broad-except
        return None
    finally:
        os.close(tty_fd)

    text = response.decode("ascii", errors="ignore")
    match = re.search(r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", text)
    if not match:
        return None
    if (
        match.group(1) == "0000"
        and match.group(2) == "0000"
        and match.group(3) == "0000"
    ):
        return None
    return match.group(0)


def _osc11_is_light(rgb: str) -> bool:
    """
    Determine if an OSC 11 rgb response represents a light background.

    Converts the 16-bit per-channel rgb string to perceived luminance using
    the standard ITU-R BT.709 coefficients. A luminance above 0.5 (mid-point
    of the 0.0–1.0 scale) is treated as a light background.

    Formula: Y = 0.2126R + 0.7152G + 0.0722B

    Args:
        rgb: A string of the form ``'rgb:RRRR/GGGG/BBBB'`` where each
             component is a 16-bit hex value (0000–ffff).

    Returns:
        True if the background is light, False if dark.
    """
    match = re.search(r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", rgb)
    if not match:
        return False

    # Normalise to 0.0–1.0 based on actual hex length (8-bit=2 chars, 16-bit=4 chars)
    def _norm(hex_str: str) -> float:
        max_val = (1 << (len(hex_str) * 4)) - 1
        return int(hex_str, 16) / max_val

    r = _norm(match.group(1))
    g = _norm(match.group(2))
    b = _norm(match.group(3))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance > 0.5


def _windows_is_light() -> bool:
    """
    Detect terminal background brightness on Windows via the console API.

    Uses ``ctypes`` to call ``GetConsoleScreenBufferInfo`` and reads the
    ``wAttributes`` field. The background color occupies bits 4–6 of
    wAttributes as a 3-bit RGB value (each bit = one color channel at full
    intensity). We compute the luminance of that color and treat values
    above 0.5 as a light background.

    Returns False (dark) on any error — ctypes unavailable, not a real
    console, or the API call fails.

    Only called on ``sys.platform == 'win32'``.
    """
    windll = getattr(_ctypes, "windll", None)
    if windll is None:
        return False
    try:

        class Coord(_ctypes.Structure):  # pylint: disable=too-few-public-methods
            _fields_ = [("X", _ctypes.c_short), ("Y", _ctypes.c_short)]

        class SmallRect(_ctypes.Structure):  # pylint: disable=too-few-public-methods
            _fields_ = [
                ("Left", _ctypes.c_short),
                ("Top", _ctypes.c_short),
                ("Right", _ctypes.c_short),
                ("Bottom", _ctypes.c_short),
            ]

        class ConsoleScreenBufferInfo(
            _ctypes.Structure
        ):  # pylint: disable=too-few-public-methods
            _fields_ = [
                ("dwSize", Coord),
                ("dwCursorPosition", Coord),
                ("wAttributes", _ctypes.c_ushort),
                ("srWindow", SmallRect),
                ("dwMaximumWindowSize", Coord),
            ]

        handle = windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        info = ConsoleScreenBufferInfo()
        if not windll.kernel32.GetConsoleScreenBufferInfo(handle, _ctypes.byref(info)):
            return False
        attrs = info.wAttributes
        bg_r = (attrs >> 6) & 1
        bg_g = (attrs >> 5) & 1
        bg_b = (attrs >> 4) & 1
        luminance = 0.2126 * bg_r + 0.7152 * bg_g + 0.0722 * bg_b
        return luminance > 0.5
    except Exception:  # pylint: disable=broad-except
        return False


def _detect_colorfgbg() -> Optional[Theme]:
    """
    Detect theme from $COLORFGBG — set by xterm, iTerm2, urxvt, Konsole.

    Format: 'fg;bg' or 'fg;...;bg'. Last segment is the background color
    index: index >= 7 means a light background.

    Returns 'light', 'dark', or None if the variable is absent or malformed.
    """
    colorfgbg = os.environ.get("COLORFGBG", "").strip()
    if not colorfgbg:
        return None
    try:
        bg = int(colorfgbg.split(";")[-1])
        return "light" if bg >= 7 else "dark"
    except ValueError:
        return None


def _detect_osc11() -> Optional[Theme]:
    """
    Detect theme via OSC 11 terminal background color query.

    Delegates to _query_osc11() for the actual query and _osc11_is_light()
    for luminance calculation. Returns None if the query was skipped or
    timed out.
    """
    rgb = _query_osc11()
    if rgb is None:
        return None
    return "light" if _osc11_is_light(rgb) else "dark"


def _detect_term_program() -> Optional[Theme]:
    """
    Detect theme from terminal-specific environment variables.

    Checks multiple environment variables set by specific terminal emulators
    at startup. Each terminal has its own convention for signaling its theme:

    - ``$TERM_PROGRAM=Apple_Terminal`` — macOS Terminal.app, almost always
      configured with a light background (system default).

    - ``$TERM_PROGRAM=vscode`` — VS Code integrated terminal. VS Code sets
      ``$VSCODE_THEME_KIND`` to ``'vscode-light'``, ``'vscode-dark'``, or
      ``'vscode-high-contrast'`` allowing precise detection.

    - ``$TERMINAL_EMULATOR=JetBrains-JediTerm`` — JetBrains IDEs (IntelliJ,
      PyCharm, GoLand, etc.). JetBrains sets ``$TERMINAL_BACKGROUND`` to
      ``'light'`` or ``'dark'`` for precise detection.

    Returns ``'light'``, ``'dark'``, or ``None`` if no match found.
    """
    term_program = os.environ.get("TERM_PROGRAM", "")

    # Apple Terminal — almost always light on macOS (system default)
    if term_program == "Apple_Terminal":
        return "light"

    # VS Code — reads $VSCODE_THEME_KIND for precise detection
    if term_program == "vscode":
        vscode_theme = os.environ.get("VSCODE_THEME_KIND", "").lower()
        if "light" in vscode_theme:
            return "light"
        if "dark" in vscode_theme or "high-contrast" in vscode_theme:
            return "dark"
        # $VSCODE_THEME_KIND absent — fall through to next detector
        return None

    # JetBrains IDEs — reads $TERMINAL_BACKGROUND for precise detection
    if os.environ.get("TERMINAL_EMULATOR") == "JetBrains-JediTerm":
        jetbrains_bg = os.environ.get("TERMINAL_BACKGROUND", "").lower()
        if jetbrains_bg == "light":
            return "light"
        if jetbrains_bg == "dark":
            return "dark"
        # $TERMINAL_BACKGROUND absent — fall through to next detector
        return None

    return None


def _detect_windows() -> Optional[Theme]:
    """
    Detect theme via Windows console API.

    Only active on win32. Delegates to _windows_is_light() for the actual
    API call. Returns None on non-Windows platforms.
    """
    platform = sys.platform  # indirection avoids static-evaluation warning
    if platform != "win32":
        return None
    return "light" if _windows_is_light() else "dark"


def detect_theme() -> Theme:
    """
    Infer the terminal background theme from multiple sources, in priority order.

    Detection chain:

    1. **$GLAZE_THEME** — explicit user override. Accepts ``dark``, ``light``,
       or ``auto`` (which continues down the chain). This is the escape hatch
       for users whose terminal doesn't report its theme reliably.

    2. **$COLORFGBG** — set by xterm, iTerm2, urxvt, and Konsole at terminal
       startup. Format: ``fg;bg`` or ``fg;...;bg``. The last segment is the
       background color index: index ≥ 7 means a light background.

    3. **OSC 11 query** — sends ``ESC ] 11 ; ? ESC \\`` to the terminal and
       reads the ``rgb:RRRR/GGGG/BBBB`` response. Supported by Ghostty, Kitty,
       WezTerm, and most modern terminals. Skipped in tmux/screen sessions,
       non-TTY environments, and when the response is pure black (known buggy
       terminals). Uses a 100ms timeout to avoid hanging in hostile environments.

    4. **$TERM_PROGRAM** — ``Apple_Terminal`` is almost always a light-background
       terminal (macOS default). Used as a weak heuristic when OSC 11 is
       unavailable.

    5. **Windows console API** — on ``win32``, queries ``GetConsoleScreenBufferInfo``
       via ctypes to read the background color attribute directly.

    6. **Fallback → dark** — the safest default. Unknown terminals are more
       likely to be dark than light, and dark-on-dark is less harmful than
       light-on-light.

    Returns:
        ``'light'`` or ``'dark'`` — never ``'auto'``.
    """
    # 1. Explicit user override via environment variable
    glaze_theme = os.environ.get("GLAZE_THEME", "").strip().lower()
    if glaze_theme in ("dark", "light"):
        return glaze_theme  # type: ignore[return-value]
    # GLAZE_THEME=auto falls through to the detection chain below

    # 2–5. Try each detector in priority order, return first match
    detected = (
        _detect_colorfgbg()
        or _detect_osc11()
        or _detect_term_program()
        or _detect_windows()
    )
    return detected if detected is not None else "dark"


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


@contextmanager
def theme_context(theme: Theme):
    """Context manager that switches theme and restores previous palette on exit."""
    global _active_palette  # pylint: disable=global-statement
    previous = _active_palette
    set_theme(theme)
    try:
        yield
    finally:
        _active_palette = previous


@contextmanager
def no_color_context():
    """Context manager that forces NO_COLOR=True and restores on exit. For use in tests."""
    global _NO_COLOR  # pylint: disable=global-statement
    previous = _NO_COLOR
    _NO_COLOR = True
    try:
        yield
    finally:
        _NO_COLOR = previous


def get_active_palette() -> Dict[str, str]:
    """Return the currently active palette. For use in tests."""
    return _active_palette


def set_active_palette(palette: Dict[str, str]) -> None:
    """Set the active palette directly. For use in tests."""
    global _active_palette  # pylint: disable=global-statement
    _active_palette = palette


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
    "get_active_palette",
    "set_active_palette",
    "theme_context",
    "no_color_context",
]
