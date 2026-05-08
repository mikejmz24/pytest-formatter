Feature: Theme selection for pytest-glaze output

  As a developer using pytest-glaze
  I want to control the color theme of the output
  So that test results are readable on both dark and light terminal backgrounds

  Scenario: Default theme auto-detects a dark terminal
    Given the environment variable COLORFGBG is set to "15;0"
    And the --glaze-theme flag is not provided
    When pytest-glaze is configured
    Then the dark color palette is active

  Scenario: Default theme auto-detects a light terminal
    Given the environment variable COLORFGBG is set to "0;7"
    And the --glaze-theme flag is not provided
    When pytest-glaze is configured
    Then the light color palette is active

  Scenario: User explicitly selects the dark theme
    Given the --glaze-theme flag is set to "dark"
    When pytest-glaze is configured
    Then the dark color palette is active

  Scenario: User explicitly selects the light theme
    Given the --glaze-theme flag is set to "light"
    When pytest-glaze is configured
    Then the light color palette is active

  Scenario: Explicit flag overrides the terminal environment
    Given the environment variable COLORFGBG is set to "0;7"
    And the --glaze-theme flag is set to "dark"
    When pytest-glaze is configured
    Then the dark color palette is active

  Scenario: Unknown or malformed COLORFGBG falls back to dark
    Given the environment variable COLORFGBG is set to "garbage"
    And the --glaze-theme flag is not provided
    When pytest-glaze is configured
    Then the dark color palette is active
