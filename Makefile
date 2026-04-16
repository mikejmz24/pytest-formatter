# ── Settings ─────────────────────────────────────────────────────────────────

PYTHON   := python
PYTEST   := uv run python -m pytest
TESTS    := tests/

# Core formatter flags.
# -p no:terminal   → silence the default reporter
# -p pytest_glaze → load our plugin (PYTHONPATH=. makes it importable)
FMT := --glaze

# Optional pass-through vars:
#   make test SUITE=tests/test_entities.py   → single suite
#   make test CASE=test_return_statuses_dict → single test by name
#   make test K="sprint and not slow"        → keyword expression
#   make test ARGS="--co -q"                 → arbitrary extra flags
SUITE ?=
CASE  ?=
K     ?=
ARGS  ?=

# Build the target path: SUITE if given, otherwise the whole TESTS dir.
_PATH := $(if $(SUITE),$(SUITE),$(TESTS))

# Build the -k filter: prefer K, fall back to CASE.
_KFLAG := $(if $(K),-k "$(K)",$(if $(CASE),-k "$(CASE)",))

BDD_TESTS := tests/corpus/test_bdd.py \
             tests/corpus/test_bdd_background.py \
             tests/corpus/test_bdd_edge_cases.py

# ── Primary targets ───────────────────────────────────────────────────────────

.PHONY: test test-fast test-corpus test-bdd test-bdd-gherkin test-bdd-gherkin-vv \
        test-bdd-json test-bdd-json-expanded test-unit test-raw help

## test           Run suite with custom output.
##                SUITE=, CASE=, K= for filtering.  ARGS= for raw pytest flags.
##                Examples:
##                  make test
##                  make test SUITE=tests/test_entities.py
##                  make test CASE=test_return_statuses_dict
##                  make test K="sprint and not slow"
test:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(_PATH) $(_KFLAG) $(ARGS)

## test-fast      Stop on first failure (-x). Accepts same filters as `test`.
test-fast:
	@PYTHONPATH=. $(PYTEST) $(FMT) -x $(_PATH) $(_KFLAG) $(ARGS)

## test-corpus    Run the formatter's own validation corpus (tests/corpus/).
##                These tests are designed to exercise every output type —
##                intentional failures are expected and correct.
test-corpus:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/corpus/ $(ARGS)

## test-bdd           Run BDD corpus through glaze formatter.
test-bdd:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(BDD_TESTS) $(ARGS)

## test-bdd-gherkin   BDD corpus with pytest-bdd's built-in Gherkin terminal
##                    reporter. Shows Feature/Scenario/step lines natively.
##                    Use -v for step names, -vv for full detail.
test-bdd-gherkin:
	@PYTHONPATH=. $(PYTEST) --gherkin-terminal-reporter -v $(BDD_TESTS) $(ARGS)

## test-bdd-gherkin-vv  Same but with full diff output on failures.
test-bdd-gherkin-vv:
	@PYTHONPATH=. $(PYTEST) --gherkin-terminal-reporter -vv $(BDD_TESTS) $(ARGS)

## test-bdd-json      BDD corpus with Cucumber JSON output.
##                    Pipe-friendly — useful for CI integrations.
test-bdd-json:
	@PYTHONPATH=. $(PYTEST) --cucumber-json=bdd-report.json $(BDD_TESTS) $(ARGS)
	@echo "Report written to bdd-report.json"

## test-bdd-json-expanded  Cucumber JSON with Scenario Outlines expanded
##                          into individual scenarios.
test-bdd-json-expanded:
	@PYTHONPATH=. $(PYTEST) --cucumber-json-expanded=bdd-report-expanded.json $(BDD_TESTS) $(ARGS)
	@echo "Report written to bdd-report-expanded.json"

## test-unit      Run unit tests only (test_parsers, test_colorizer, test_plugin).
##                No intentional failures — clean pass/fail signal.
test-unit:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/test_parsers.py tests/test_colorizer.py tests/test_plugin.py $(_KFLAG) $(ARGS)

## test-raw       Raw default pytest output. Useful for debugging the formatter.
test-raw:
	@$(PYTEST) $(_PATH) $(_KFLAG) $(ARGS)

## help           List all targets.
help:
	@grep -E '^##' Makefile | sed 's/^## /  /'
