"""
pytest_glaze — Opinionated pytest output formatter.

Public API. Everything else is internal.
"""

from pytest_glaze._colorizer import LineColorizer
from pytest_glaze._formatter import FormatterPlugin

# Hook functions discovered automatically by pytest via entry_points.
# Re-exported here so pytest can find them when the package is loaded.
from pytest_glaze._hooks import (
    pytest_addoption,
    pytest_bdd_after_step,
    pytest_bdd_before_scenario,
    pytest_bdd_before_step,
    pytest_bdd_step_error,
    pytest_bdd_step_func_lookup_error,
    pytest_configure,
)

__all__ = [
    "FormatterPlugin",
    "LineColorizer",
    "pytest_addoption",
    "pytest_configure",
    "pytest_bdd_before_scenario",
    "pytest_bdd_before_step",
    "pytest_bdd_after_step",
    "pytest_bdd_step_error",
    "pytest_bdd_step_func_lookup_error",
]
