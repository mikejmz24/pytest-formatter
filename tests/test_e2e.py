# ── Plugin activation ─────────────────────────────────────────────────────────


def test_glaze_flag_activates_formatter(pytester):
    """--glaze flag must activate the formatter and suppress default output."""
    pytester.makepyfile("""
        def test_pass():
            assert 1 == 1
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*PASS*test_pass*"])
    assert "passed" in result.stdout.str()


def test_without_glaze_uses_default_output(pytester):
    """Without --glaze the default pytest output must be used."""
    pytester.makepyfile("""
        def test_pass():
            assert 1 == 1
    """)
    result = pytester.runpytest()
    assert "PASS" not in result.stdout.str()
    assert "passed" in result.stdout.str()


# ── Pass / Fail / Skip / Error ────────────────────────────────────────────────


def test_passing_test_shows_pass_badge(pytester):
    pytester.makepyfile("""
        def test_something():
            assert True
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*PASS*test_something*"])


def test_failing_test_shows_fail_badge_and_inline_error(pytester):
    pytester.makepyfile("""
        def test_bad():
            assert 3 == 30
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*FAIL*test_bad*"])
    result.stdout.fnmatch_lines(["*assert*3*==*30*"])


def test_skipped_test_shows_skip_badge(pytester):
    pytester.makepyfile("""
        import pytest
        @pytest.mark.skip(reason="not today")
        def test_skip():
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*SKIP*test_skip*"])
    assert "not today" in result.stdout.str()


def test_error_in_setup_shows_error_badge(pytester):
    pytester.makepyfile("""
        import pytest
        @pytest.fixture
        def broken():
            raise RuntimeError("setup exploded")
        def test_with_broken(broken):
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*ERROR*test_with_broken*"])
    assert "setup exploded" in result.stdout.str()


# ── Session summary ───────────────────────────────────────────────────────────


def test_total_line_appears_at_end(pytester):
    pytester.makepyfile("""
        def test_a(): pass
        def test_b(): assert False
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "Total:" in result.stdout.str()
    assert "1 passed" in result.stdout.str()
    assert "1 failed" in result.stdout.str()


def test_per_file_summary_appears(pytester):
    pytester.makepyfile("""
        def test_a(): pass
        def test_b(): pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "=>" in result.stdout.str()
    assert "2 passed" in result.stdout.str()


# ── Collection errors ─────────────────────────────────────────────────────────


def test_collection_error_surfaced(pytester):
    pytester.makepyfile("""
        import nonexistent_module_xyz
        def test_something(): pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "COLLECTION ERRORS" in result.stdout.str()


# ── Terminal safety ───────────────────────────────────────────────────────────


def test_ansi_injection_in_test_name_does_not_corrupt_output(pytester):
    """A test name containing ANSI escape sequences must not corrupt output."""
    pytester.makepyfile(r"""
        def test_normal():
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    # Output must contain readable content — not garbled by control sequences
    assert "PASS" in result.stdout.str()
    assert "Total:" in result.stdout.str()


# ── BDD session cases ─────────────────────────────────────────────────────────


def test_bdd_compact_mode_default(pytester):
    """BDD scenarios collapse to single line in compact mode by default."""
    pytester.makepyfile("""
        from pytest_bdd import scenario, given, when, then
        
        @scenario("test.feature", "Guest completes a purchase")
        def test_guest_purchase(): ...
        
        @given("the cart contains 2 items", target_fixture="cart")
        def cart(): return {"items": 2}
        
        @when("the guest submits payment")
        def submit(cart): pass
        
        @then("the order is confirmed")
        def confirmed(cart): pass
    """)
    pytester.makefile(
        ".feature",
        test="""
        Feature: Shopping cart
          Scenario: Guest completes a purchase
            Given the cart contains 2 items
            When the guest submits payment
            Then the order is confirmed
    """,
    )
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*PASS*Scenario: Guest completes a purchase*"])


def test_teardown_error_shows_after_pass(pytester):
    """Teardown errors must appear after the passing test line."""
    pytester.makepyfile("""
        import pytest
        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown exploded")
        def test_pass(broken_teardown):
            assert True
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    output = result.stdout.str()
    pass_pos = output.find("PASS")
    error_pos = output.find("ERROR")
    assert pass_pos != -1
    assert error_pos != -1
    assert pass_pos < error_pos


# ── No-color path ─────────────────────────────────────────────────────────────
# These tests verify the formatter degrades cleanly when ANSI is suppressed
# via NO_COLOR=1. They use runpytest_subprocess because:
#   1. _NO_COLOR is computed at module import time in _colors.py, so the
#      child process must see the env var before importing pytest_glaze.
#   2. The suite-wide conftest.py force-enables colors via monkeypatch —
#      that fixture leaks into runpytest() (same-process) but not into
#      runpytest_subprocess() (fresh interpreter).


_ESC = "\x1b["


def test_no_color_env_strips_ansi_from_pass_line(pytester, monkeypatch):
    """NO_COLOR=1 must produce output free of ANSI escape sequences."""
    monkeypatch.setenv("NO_COLOR", "1")
    pytester.makepyfile("""
        def test_ok():
            assert True
        """)
    result = pytester.runpytest_subprocess("--glaze", "-p", "no:terminal")
    output = result.stdout.str()
    assert "PASS" in output
    assert _ESC not in output, f"ANSI escape leaked under NO_COLOR: {output!r}"


def test_no_color_env_strips_ansi_from_fail_line(pytester, monkeypatch):
    """Failure rendering must remain readable and ANSI-free under NO_COLOR=1."""
    monkeypatch.setenv("NO_COLOR", "1")
    pytester.makepyfile("""
        def test_bad():
            assert 3 == 30
        """)
    result = pytester.runpytest_subprocess("--glaze", "-p", "no:terminal")
    output = result.stdout.str()
    assert "FAIL" in output
    assert "test_bad" in output
    assert _ESC not in output, f"ANSI escape leaked under NO_COLOR: {output!r}"


def test_no_color_env_strips_ansi_from_summary_line(pytester, monkeypatch):
    """Per-file summary and Total line must contain no ANSI under NO_COLOR=1."""
    monkeypatch.setenv("NO_COLOR", "1")
    pytester.makepyfile("""
        def test_a():
            assert True
        def test_b():
            assert True
        """)
    result = pytester.runpytest_subprocess("--glaze", "-p", "no:terminal")
    output = result.stdout.str()
    assert "Total:" in output
    assert "passed" in output
    assert _ESC not in output, f"ANSI escape leaked under NO_COLOR: {output!r}"


# ── BDD session tests ─────────────────────────────────────────────────────────
#
# Design notes for future maintainers:
#
# WHY pytester.makepyfile() / pytester.makefile():
#   These are the official pytest-recommended approach for plugin integration
#   tests. Each call creates a real file inside a unique tmp_path directory
#   that pytest manages per-test. Files are deleted automatically at session
#   end (pass or fail). The alternative — committing real test files to disk —
#   couples tests to filesystem layout and obscures intent.
#
# WHY runpytest() not runpytest_subprocess():
#   runpytest() runs in the same process (faster, ~5ms vs ~50ms per call).
#   runpytest_subprocess() spawns a fresh interpreter — required only when
#   module-level state must be isolated (e.g. _NO_COLOR is computed at import
#   time, so the no-color tests above need subprocess mode). BDD tests have
#   no such constraint, so in-process is correct here.
#
# IDEMPOTENCY:
#   Each pytester test gets its own isolated tmp directory — no shared state
#   between tests. Safe to run in any order, any number of times, or in
#   parallel via pytest-xdist.
#
# EXIT CODE ASSERTIONS (result.ret):
#   Always assert result.ret alongside output content. A silent crash in a
#   hook can produce unexpected output that accidentally satisfies a string
#   assertion. result.ret == 0 means all tests passed, result.ret == 1 means
#   at least one test failed. This makes assertions honest.
#
# PERFORMANCE NOTE:
#   makefile(".feature", ...) involves real disk I/O — negligible now but
#   worth knowing if the BDD e2e suite grows to hundreds of tests. At that
#   point, batch multiple scenarios into fewer feature files to reduce
#   per-test overhead.
#
# MAINTAINABILITY CONVENTIONS:
#   1. One assertion per concern — if you can't name the test after a single
#      behavior, split it into multiple tests.
#   2. If feature file content is shared across multiple tests, extract it
#      to a module-level constant rather than duplicating inline strings.
#   3. Keep step definitions minimal — only the steps the scenario needs.
#      Avoid fixture reuse across BDD e2e tests; self-contained is clearer.


def test_bdd_steps_flag_shows_individual_step_lines(pytester):
    """--bdd-steps must render a Given/When/Then line for each passing step.

    Verifies that the --bdd-steps flag activates full step-by-step rendering
    instead of the default compact (one line per scenario) mode. Each step
    keyword (Given/When/Then) must appear in the output, confirming that
    _bdd_flush_scenario() correctly entered steps_mode=True.

    Exit code must be 0 — if the formatter crashes during step rendering,
    result.ret would be non-zero and the test would catch the silent failure
    even if "PASS" happened to appear in a traceback.
    """
    # Feature file is created as checkout.feature in the pytester tmp dir.
    # pytest-bdd's @scenario locates it relative to the test file's directory.
    # If you need this scenario in multiple e2e tests, extract the string to
    # a module-level _CHECKOUT_FEATURE constant instead of duplicating it.
    pytester.makefile(
        ".feature",
        checkout="""
Feature: Shopping cart checkout
  Scenario: Guest completes a purchase
    Given a guest user
    When they add an item to the cart
    Then the order is confirmed
""",
    )
    pytester.makepyfile("""
        from pytest_bdd import scenario, given, when, then

        @scenario("checkout.feature", "Guest completes a purchase")
        def test_guest_purchase():
            pass

        @given("a guest user")
        def guest_user():
            pass

        @when("they add an item to the cart")
        def add_item():
            pass

        @then("the order is confirmed")
        def order_confirmed():
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal", "--bdd-steps")
    output = result.stdout.str()

    # Verify full step-by-step rendering — each keyword must appear.
    assert "Given" in output
    assert "When" in output
    assert "Then" in output
    assert "PASS" in output

    # Exit code 0 = all tests passed. Guards against silent hook crashes
    # that might still produce "PASS" in a traceback or error message.
    assert result.ret == 0, f"Expected clean exit, got ret={result.ret}:\n{output}"


def test_bdd_missing_step_definition_shows_error_badge(pytester):
    """A step with no matching definition must surface as ERROR with trimmed message.

    Verifies that _bdd_step_func_lookup_error() correctly captures the
    StepDefinitionNotFoundError, trims it to the first sentence via
    extract_exception_msg(), and renders an ERROR badge with the step text
    visible in the output.

    The 'Then the order is confirmed' step is intentionally left without a
    definition — this is the failure condition under test, not a mistake.

    Exit code must be 1 (test failed). If the formatter silently swallows
    the error and exits 0, result.ret catches it even if "ERROR" appears
    elsewhere in the output.
    """
    pytester.makefile(
        ".feature",
        checkout="""
Feature: Shopping cart checkout
  Scenario: Guest completes a purchase
    Given a guest user
    When they add an item to the cart
    Then the order is confirmed
""",
    )
    pytester.makepyfile("""
        from pytest_bdd import scenario, given, when

        @scenario("checkout.feature", "Guest completes a purchase")
        def test_guest_purchase():
            pass

        @given("a guest user")
        def guest_user():
            pass

        @when("they add an item to the cart")
        def add_item():
            pass

        # "Then the order is confirmed" has no step definition — intentional.
        # This triggers pytest_bdd_step_func_lookup_error in the formatter,
        # which must render an ERROR badge with the step text trimmed to the
        # first sentence of StepDefinitionNotFoundError.
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    output = result.stdout.str()

    # ERROR badge must appear — confirms the hook fired and rendered correctly.
    assert "ERROR" in output

    # Step text must appear in the trimmed error message — confirms
    # extract_exception_msg() surfaced the right content and didn't swallow it.
    assert "the order is confirmed" in output

    # Exit code 1 = at least one test failed, as expected.
    assert result.ret == 1, f"Expected failed exit, got ret={result.ret}:\n{output}"


def test_osc_hyperlink_in_assertion_does_not_corrupt_output(pytester):
    """OSC hyperlink escape sequences in assertion messages must be sanitized.

    OSC (Operating System Command) sequences take the form:
        ESC ]8;; <url> ESC \\ <text> ESC ]8;; ESC \\
    Modern terminals render these as clickable hyperlinks. If they reach
    stdout unsanitized they corrupt the terminal display and can break
    downstream log parsers.

    This test verifies that LineColorizer.sanitize() strips OSC sequences
    before rendering, so the link text ('click here') survives but the
    escape bytes do not.

    Uses a raw string r\"\"\"...\"\"\" so that \\x1b becomes a real ESC byte
    in the generated test file when Python parses it in the child process.
    This is intentional — do not change to a regular string, which would
    leave \\x1b as a literal backslash-x sequence and miss the real sanitization path.

    SECURITY NOTE:
    If you extend this test to cover truly hostile payloads (shell injection,
    path traversal), ensure assertions verify sanitization rather than just
    absence of a crash — a silent swallow is as dangerous as a pass-through.

    Exit code must be 1 (assertion failed in the generated test), confirming
    the formatter rendered the failure path rather than erroring out silently.
    """
    # r-string: \x1b becomes ESC byte in the child process's generated file.
    pytester.makepyfile(r"""
        def test_osc_in_message():
            # OSC hyperlink sequence: ESC ]8;; url ESC \ text ESC ]8;; ESC \
            # A hostile terminal or log injector could embed these in any
            # string that ends up in an assertion message or exception text.
            osc_link = "\x1b]8;;https://example.com\x1b\\click here\x1b]8;;\x1b\\"
            assert osc_link == "plain text", f"got: {osc_link}"
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    output = result.stdout.str()

    # Failure must be rendered — confirms the formatter reached the sanitization path.
    assert "FAIL" in output

    # OSC sequence must not appear in output — the ESC ]8; prefix is the
    # universal marker for OSC hyperlinks. If any byte of this leaks through,
    # sanitize() missed the OSC pattern.
    assert "\x1b]8;" not in output, (
        f"OSC hyperlink sequence leaked into formatter output.\n"
        f"This means LineColorizer.sanitize() is not stripping OSC sequences.\n"
        f"Output repr: {output!r}"
    )

    # Exit code 1 = assertion failed in the generated test, as expected.
    assert result.ret == 1, f"Expected failed exit, got ret={result.ret}:\n{output}"
