Feature: pytest-glaze BDD rendering

  pytest-glaze renders pytest-bdd scenarios with Feature/Scenario headers,
  per-step results, and the same color semantics as regular tests.
  Compact mode is the default — PASS scenarios collapse to one line.
  Failures always show full step-by-step output.

  # ── Compact mode (default) ───────────────────────────────────────────────────

  Scenario: Passing scenario renders as a single compact line in compact mode
    Given a passing BDD scenario with 3 steps
    When pytest-glaze flushes the scenario in compact mode
    Then the output contains a PASS badge
    And the scenario name appears on the result line
    And no step lines are printed

  Scenario: Compact line shows total duration of all steps
    Given a passing BDD scenario with 3 steps each taking 0.1 seconds
    When pytest-glaze flushes the scenario in compact mode
    Then the duration shown is the sum of all step durations

  Scenario: Failing scenario shows full steps in compact mode
    Given a BDD scenario where the last step fails
    When pytest-glaze flushes the scenario in compact mode
    Then all step lines are printed
    And the failing step has a FAIL badge

  Scenario: Error scenario shows full steps in compact mode
    Given a BDD scenario where a step raises a RuntimeError
    When pytest-glaze flushes the scenario in compact mode
    Then all step lines are printed
    And the error step has an ERROR badge

  Scenario: Skipped scenario renders as a single compact line
    Given a skipped BDD scenario
    When pytest-glaze renders the skip result
    Then the output contains a SKIP badge
    And the scenario name appears on the result line

  Scenario: Xfailed scenario renders as a single compact line
    Given a BDD scenario where the last step is xfailed
    When pytest-glaze flushes the scenario in compact mode
    Then the output contains an XFAIL badge
    And no step lines are printed

  Scenario: Xpassed scenario renders as a single compact line
    Given a BDD scenario where the last step is xpassed
    When pytest-glaze flushes the scenario in compact mode
    Then the output contains an XPASS badge
    And no step lines are printed

  # ── Full steps mode (--bdd-steps) ────────────────────────────────────────────

  Scenario: Passing scenario shows all steps in steps mode
    Given a passing BDD scenario with 3 steps
    When pytest-glaze flushes the scenario in steps mode
    Then exactly 3 step lines are printed
    And each step line has a PASS badge

  Scenario: Steps mode shows step keyword and name
    Given a passing BDD scenario with a "Given" step named "the cart contains 2 items"
    When pytest-glaze flushes the scenario in steps mode
    Then the step line contains "Given"
    And the step line contains "the cart contains 2 items"

  # ── Feature and Scenario headers ─────────────────────────────────────────────
  
  Scenario: Feature header renders in baby blue
    Given a BDD scenario in feature "Shopping cart checkout"
    When pytest-glaze processes the scenario
    Then the Feature header is baby blue

Scenario: Scenario header renders in steel blue
    Given a BDD scenario in feature "Shopping cart checkout"
    When pytest-glaze processes the scenario in steps mode
    Then the Scenario header is steel blue

  Scenario: Feature header prints before first scenario
    Given a BDD scenario in feature "Shopping cart checkout"
    When pytest-glaze processes the scenario
    Then the Feature header "Shopping cart checkout" appears before the scenario

  Scenario: Feature header does not repeat for same feature
    Given two BDD scenarios in the same feature "Shopping cart checkout"
    When pytest-glaze processes the same feature twice
    Then "Shopping cart checkout" appears exactly once as a Feature header

  Scenario: New feature prints a blank line then a new header
    Given a BDD scenario in feature "Shopping cart checkout"
    And another BDD scenario in feature "User authentication"
    When pytest-glaze processes both scenarios
    Then a blank line appears before "User authentication" feature header

  # ── Step outcomes and colors ──────────────────────────────────────────────────

  Scenario: Passing step renders entirely in green
    Given a passing BDD scenario with 1 step
    When pytest-glaze flushes the scenario in steps mode
    Then the step line is entirely green
    And the step "---" prefix is green
    And the step "PASS" badge is green
    And the step name is green

  Scenario: Failing step renders entirely in bright red
    Given a BDD scenario where the last step fails
    When pytest-glaze flushes the scenario in steps mode
    Then the step line is entirely bright red
    And the failing step "---" prefix is bright red
    And the failing step "FAIL" badge is bright red
    And the step name is bright red

  Scenario: Error step renders entirely in standard red
    Given a BDD scenario where a step raises a RuntimeError
    When pytest-glaze flushes the scenario in steps mode
    Then the step line is entirely standard red
    And the error step "---" prefix is standard red
    And the error step "ERROR" badge is standard red
    And the step name is standard red

  Scenario: Xfailed step renders entirely in bright red
    Given a BDD scenario where the last step is xfailed
    When pytest-glaze flushes the scenario in steps mode
    Then the step line is entirely bright red
    And the step "XFAIL" badge is bright red

  Scenario: Xpassed step renders entirely in yellow
    Given a BDD scenario where the last step is xpassed
    When pytest-glaze flushes the scenario in steps mode
    Then the step line is entirely yellow
    And the step "XPASS" badge is yellow

  Scenario: Compact PASS line entire line renders in green
    Given a passing BDD scenario with 1 step
    When pytest-glaze flushes the scenario in compact mode
    Then the entire compact result line is green

  Scenario: Compact FAIL scenario name renders in bright red
    Given a BDD scenario where the last step fails
    When pytest-glaze flushes the scenario in compact mode
    Then the scenario name on the FAIL line is bright red

  Scenario: Compact SKIP line renders entirely in yellow
    Given a skipped BDD scenario
    When pytest-glaze renders the skip result
    Then the entire compact result line is yellow

  Scenario: Compact XFAIL line renders entirely in bright red
    Given a BDD scenario where the last step is xfailed
    When pytest-glaze flushes the scenario in compact mode
    Then the entire compact result line is bright red

  Scenario: Compact XPASS line renders entirely in yellow
    Given a BDD scenario where the last step is xpassed
    When pytest-glaze flushes the scenario in compact mode
    Then the entire compact result line is yellow

  # ── Xfail and Xpass correction ────────────────────────────────────────────────

  Scenario: Xfail corrects last step from failed to xfailed
    Given a BDD scenario where the last step is xfailed
    When pytest-glaze flushes the scenario in steps mode
    Then the last step has an XFAIL badge
    And the xfail reason appears on the E line

  Scenario: Xpass corrects last step from passed to xpassed
    Given a BDD scenario where the last step is xpassed
    When pytest-glaze flushes the scenario in steps mode
    Then the last step has an XPASS badge

  # ── Step not found ────────────────────────────────────────────────────────────

  Scenario: Missing step definition renders as ERROR with trimmed message
    Given a BDD scenario where a step has no implementation
    When pytest-glaze flushes the scenario in steps mode
    Then the step has an ERROR badge
    And the error message is trimmed to the first sentence

  # ── Background steps ──────────────────────────────────────────────────────────

  Scenario: Background label appears before first background step
    Given a BDD scenario with a background step
    When pytest-glaze flushes the scenario in steps mode
    Then a dim "Background:" label appears before the background step

  # ── Teardown errors ───────────────────────────────────────────────────────────

Scenario: Teardown error renders after passing scenario
    Given a passing BDD scenario with 2 steps for teardown
    And a teardown error "RuntimeError: cleanup failed"
    When pytest-glaze renders the teardown error
    Then the teardown error line shows "teardown failed"
    And the error message appears on the E line
