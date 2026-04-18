# tests/test_bdd_plugin.py
"""
Unit tests for BDD helper methods in FormatterPlugin.

Same patterns as test_plugin.py — SimpleNamespace stubs, no pytest machinery.
All methods tested in pure isolation by inspecting _bdd_scenario_buf directly
rather than capturing printed output.

Coverage:
  _extract_exception_msg    — exception → concise E-line string
  _bdd_before_scenario      — Feature/Scenario header buffering, blank line rules
  _bdd_after_step           — PASS step buffering, handled set, last_step_idx
  _bdd_step_error           — FAIL/ERROR step buffering, message capture
  _bdd_flush_scenario       — xfail/xpass correction, buffer cleared after flush
  _bdd_before_step          — start time recording, Background label insertion
"""
from types import SimpleNamespace

import pytest_glaze
from pytest_glaze import FormatterPlugin, _BDDStep

# Force ANSI codes regardless of terminal detection.
pytest_glaze._NO_COLOR = False


# ── Stubs ─────────────────────────────────────────────────────────────────────

def _plugin() -> FormatterPlugin:
    """Fresh FormatterPlugin with _glaze_plugin wired up."""
    p = FormatterPlugin()
    pytest_glaze._glaze_plugin = p
    return p


def _feature(name: str = "Shopping cart checkout", background=None):
    return SimpleNamespace(name=name, background=background)


def _scenario(name: str = "Guest completes a purchase"):
    return SimpleNamespace(name=name)


def _step(keyword: str = "Given", type_: str = "given", name: str = "the cart contains 2 items"):
    return SimpleNamespace(keyword=keyword, type=type_, name=name)


def _request(nodeid: str = "tests/bdd/test_checkout.py::test_guest_purchase"):
    return SimpleNamespace(node=SimpleNamespace(nodeid=nodeid))


def _buf_strings(p: FormatterPlugin) -> list:
    """Return only string items from _bdd_scenario_buf (excludes _BDDStep instances)."""
    return [item for item in p._bdd_scenario_buf if isinstance(item, str)]


def _buf_steps(p: FormatterPlugin) -> list:
    """Return only _BDDStep items from _bdd_scenario_buf."""
    return [item for item in p._bdd_scenario_buf if isinstance(item, _BDDStep)]


# ── _extract_exception_msg ────────────────────────────────────────────────────

class TestExtractExceptionMsg:
    """Tests for FormatterPlugin._extract_exception_msg()."""

    def test_assertion_error_does_not_prepend_type_name(self):
        # pytest assertion rewriting already includes 'assert' in the message.
        # _extract_exception_msg preserves it as-is without prepending 'AssertionError:'.
        msg = FormatterPlugin._extract_exception_msg(AssertionError("assert 95.0 == 90"))
        assert msg == "assert 95.0 == 90"

    def test_assertion_error_includes_message_body(self):
        msg = FormatterPlugin._extract_exception_msg(AssertionError("assert 95.0 == 90"))
        assert "assert 95.0 == 90" in msg

    def test_runtime_error_prepends_type(self):
        msg = FormatterPlugin._extract_exception_msg(RuntimeError("inventory timed out"))
        assert msg == "RuntimeError: inventory timed out"

    def test_connection_error_prepends_type(self):
        msg = FormatterPlugin._extract_exception_msg(ConnectionError("could not reach db.internal"))
        assert msg.startswith("ConnectionError:")

    def test_empty_exception_returns_type_name(self):
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(""))
        assert msg == "RuntimeError"

    def test_multiline_trimmed_to_max_e_lines(self):
        """More than MAX_E_LINES lines must be truncated."""
        big = "\n".join(f"line {i}" for i in range(30))
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(big))
        assert len(msg.splitlines()) == pytest_glaze.MAX_E_LINES

    def test_blank_lines_excluded_from_count(self):
        """Blank lines in the exception message must not count toward MAX_E_LINES."""
        lines = "\n\n".join(f"line {i}" for i in range(20))
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(lines))
        assert msg is not None


# ── _bdd_before_scenario: Feature header ─────────────────────────────────────

class TestBddBeforeScenarioFeatureHeader:
    """Buffer contents for Feature header — when it appears and when it doesn't."""

    def test_first_scenario_buffers_feature_header(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        assert any("Feature:" in s and "Shopping cart checkout" in s for s in strings)

    def test_first_scenario_no_blank_line_before_feature(self):
        """The very first feature must not be preceded by a blank line."""
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        feature_idx = next(i for i, s in enumerate(strings) if "Feature:" in s)
        assert "" not in strings[:feature_idx]

    def test_new_feature_blank_line_buffered_before_header(self):
        """When the feature changes, a blank line must precede the new Feature header."""
        p = _plugin()
        p._bdd_cur_feature       = "Old Feature"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature("Shopping cart checkout"), _scenario())
        strings = _buf_strings(p)
        feature_idx = next(i for i, s in enumerate(strings) if "Feature:" in s)
        assert strings[feature_idx - 1] == ""

    def test_same_feature_no_duplicate_header(self):
        """Consecutive scenarios of the same feature must not repeat the header."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        assert not any("Feature:" in s for s in strings)

    def test_cur_feature_updated_to_new_name(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature("New Feature"), _scenario())
        assert p._bdd_cur_feature == "New Feature"

    def test_any_feature_printed_flag_set_after_first(self):
        p = _plugin()
        assert p._bdd_any_feature_printed is False
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert p._bdd_any_feature_printed is True


# ── _bdd_before_scenario: Scenario header ────────────────────────────────────

class TestBddBeforeScenarioScenarioHeader:
    """Buffer contents for Scenario header and blank-line spacing."""

    def test_scenario_name_in_buffer(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario("Guest completes a purchase"))
        strings = _buf_strings(p)
        assert any("Scenario:" in s and "Guest completes a purchase" in s for s in strings)

    def test_blank_line_between_same_feature_scenarios(self):
        """Two scenarios in the same feature must be separated by a blank line."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature(), _scenario("Scenario B"))
        strings = _buf_strings(p)
        assert "" in strings

    def test_feature_header_before_scenario_header(self):
        """Feature header must always precede the Scenario header in the buffer."""
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        feature_idx  = next(i for i, s in enumerate(strings) if "Feature:" in s)
        scenario_idx = next(i for i, s in enumerate(strings) if "Scenario:" in s)
        assert feature_idx < scenario_idx

    def test_buffer_reset_on_each_scenario(self):
        """Each call to _bdd_before_scenario must start with a fresh buffer."""
        p = _plugin()
        p._bdd_scenario_buf = ["stale content"]
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert "stale content" not in p._bdd_scenario_buf

    def test_last_step_idx_reset_to_minus_one(self):
        p = _plugin()
        p._bdd_last_step_idx = 5
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert p._bdd_last_step_idx == -1


# ── _bdd_after_step ───────────────────────────────────────────────────────────

class TestBddAfterStep:
    """Tests for _bdd_after_step — PASS step buffering."""

    import time as _time

    def _run(self, p, step=None, nodeid="tests/bdd/test_checkout.py::test_guest_purchase"):
        import time
        step = step or _step()
        p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_after_step(_request(nodeid), _feature(), _scenario(), step, None, {})
        return step

    def test_adds_pass_step_to_buffer(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert len(_buf_steps(p)) == 1
        assert _buf_steps(p)[0].outcome == "passed"

    def test_step_name_preserved(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step(name="the cart contains 2 items")
        import time; p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_after_step(_request(), _feature(), _scenario(), step, None, {})
        assert _buf_steps(p)[0].step.name == "the cart contains 2 items"

    def test_nodeid_added_to_handled(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, nodeid="tests/bdd/test_checkout.py::test_guest_purchase")
        assert "tests/bdd/test_checkout.py::test_guest_purchase" in p._bdd_handled

    def test_last_step_idx_updated(self):
        p = _plugin()
        p._bdd_scenario_buf = ["header string"]
        self._run(p)
        assert p._bdd_last_step_idx == 1  # header at 0, step at 1

    def test_short_msg_is_none_for_passing_step(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert _buf_steps(p)[0].short_msg is None


# ── _bdd_step_error ───────────────────────────────────────────────────────────

class TestBddStepError:
    """Tests for _bdd_step_error — FAIL/ERROR step buffering."""

    def _run(self, p, exc, step=None, nodeid="tests/bdd/test_checkout.py::test_discount_code"):
        import time
        step = step or _step()
        p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_step_error(_request(nodeid), _feature(), _scenario(), step, None, {}, exc)
        return step

    def test_assertion_error_outcome_is_failed(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, AssertionError("assert 95.0 == 90"))
        assert _buf_steps(p)[0].outcome == "failed"

    def test_runtime_error_outcome_is_error(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, RuntimeError("inventory service timed out"))
        assert _buf_steps(p)[0].outcome == "error"

    def test_connection_error_outcome_is_error(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, ConnectionError("could not reach db.internal:5432"))
        assert _buf_steps(p)[0].outcome == "error"

    def test_short_msg_captured(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, RuntimeError("inventory service timed out after 5000ms"))
        assert "inventory service timed out after 5000ms" in _buf_steps(p)[0].short_msg

    def test_nodeid_added_to_handled(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, AssertionError("x"), nodeid="tests/bdd/test_checkout.py::test_discount_code")
        assert "tests/bdd/test_checkout.py::test_discount_code" in p._bdd_handled

    def test_last_step_idx_updated(self):
        p = _plugin()
        p._bdd_scenario_buf = ["header"]
        self._run(p, AssertionError("x"))
        assert p._bdd_last_step_idx == 1


# ── _bdd_flush_scenario ───────────────────────────────────────────────────────

class TestBddFlushScenario:
    """Tests for _bdd_flush_scenario — xfail/xpass correction and buffer clearing."""

    def _make_step_buf(self, p, outcome="passed", short_msg=None):
        bdd_step = _BDDStep(step=_step(), outcome=outcome, duration=0.1, short_msg=short_msg)
        p._bdd_scenario_buf  = [bdd_step]
        p._bdd_last_step_idx = 0
        p._p = lambda t="": None  # suppress output
        return bdd_step

    def test_xfail_corrects_last_step_outcome(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed")
        p._bdd_flush_scenario("xfailed", "xfailed: known bug")
        assert bdd_step.outcome == "xfailed"

    def test_xfail_corrects_last_step_message(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed", "assert x")
        p._bdd_flush_scenario("xfailed", "xfailed: known bug")
        assert bdd_step.short_msg == "xfailed: known bug"

    def test_xpass_corrects_last_step_outcome(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "passed")
        p._bdd_flush_scenario("xpassed", "xpassed: bug was fixed")
        assert bdd_step.outcome == "xpassed"

    def test_passed_does_not_modify_last_step(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "passed")
        p._bdd_flush_scenario("passed", None)
        assert bdd_step.outcome == "passed"

    def test_failed_does_not_modify_last_step(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed")
        p._bdd_flush_scenario("failed", "assert x")
        assert bdd_step.outcome == "failed"

    def test_buffer_cleared_after_flush(self):
        p = _plugin()
        self._make_step_buf(p)
        p._bdd_flush_scenario("passed", None)
        assert p._bdd_scenario_buf == []

    def test_last_step_idx_reset_after_flush(self):
        p = _plugin()
        self._make_step_buf(p)
        p._bdd_flush_scenario("passed", None)
        assert p._bdd_last_step_idx == -1

    def test_blank_string_items_printed(self):
        """Empty string items in the buffer must trigger a blank line print."""
        p = _plugin()
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_scenario_buf  = [""]
        p._bdd_last_step_idx = -1
        p._bdd_flush_scenario("passed", None)
        assert "" in printed

    def test_no_crash_when_buffer_empty(self):
        p = _plugin()
        p._p = lambda t="": None
        p._bdd_flush_scenario("passed", None)  # must not raise


# ── _bdd_before_step ──────────────────────────────────────────────────────────

class TestBddBeforeStep:
    """Tests for _bdd_before_step — timing and Background label insertion."""

    def test_records_step_start_time(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        p._bdd_before_step(_request(), _feature(), _scenario(), step, None)
        assert id(step) in p._bdd_step_t0

    def test_background_label_added_for_first_bg_step(self):
        """The first background step must cause a 'Background:' label to be buffered."""
        p = _plugin()
        p._bdd_scenario_buf = []
        bg_step = _step("Given", "given", "the database is available")
        feature = SimpleNamespace(
            name="Auth",
            background=SimpleNamespace(steps=[bg_step])
        )
        p._bdd_before_step(_request(), feature, _scenario(), bg_step, None)
        strings = _buf_strings(p)
        assert any("Background:" in s for s in strings)

    def test_no_background_label_for_regular_step(self):
        """Steps from the scenario body must not trigger a Background label."""
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        feature = _feature()   # background=None
        p._bdd_before_step(_request(), feature, _scenario(), step, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)

    def test_no_background_label_for_second_bg_step(self):
        """Only the FIRST background step gets the label — subsequent ones do not."""
        p = _plugin()
        p._bdd_scenario_buf = []
        bg_step1 = _step("Given", "given", "step one")
        bg_step2 = _step("And",   "given", "step two")
        feature = SimpleNamespace(
            name="Auth",
            background=SimpleNamespace(steps=[bg_step1, bg_step2])
        )
        p._bdd_before_step(_request(), feature, _scenario(), bg_step2, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)

    def test_no_background_label_when_background_has_no_steps(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        feature = SimpleNamespace(name="Auth", background=SimpleNamespace(steps=[]))
        p._bdd_before_step(_request(), feature, _scenario(), step, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)
