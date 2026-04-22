"""
pytest_glaze/_types.py — Shared types and constants.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

MAX_E_LINES: int = 15


@dataclass
class TestResult:
    """Normalised result for a single test, ready for rendering."""

    nodeid:    str
    file:      str
    name:      str
    outcome:   str                        # one of _OUTCOME_ORDER
    duration:  float                      # seconds
    short_msg: Optional[str] = None       # one-liner shown on the E line
    sections:  List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class _BDDStep:
    """Buffered BDD step waiting to be rendered at scenario flush time."""

    step:      Any
    outcome:   str
    duration:  float
    short_msg: Optional[str]

__all__ = ["MAX_E_LINES", "TestResult", "_BDDStep"]
