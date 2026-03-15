Feature: Reference-aware generation and backend fallback
  In order to support multiple image backends cleanly
  As an Evennia game using evennia-ai-image-generator
  I want the system to use references when available and degrade gracefully when features are unsupported

  Scenario: Room refresh uses prior room image when backend supports img2img
    Given a room has a current image
    And the selected backend supports "img2img"
    When a backend generation request is built for the room
    Then the prior room image is included as a continuity reference

  Scenario: Object refresh uses prior object image when backend supports img2img
    Given an object has a current image
    And the selected backend supports "img2img"
    When a backend generation request is built for the object
    Then the prior object image is included as a continuity reference

  Scenario: Continuity falls back when img2img is unavailable
    Given a subject has a current image
    And the selected backend does not support "img2img"
    When a backend generation request is built
    Then the system falls back to a supported mode
    And the request still reflects the current textual state of the subject

  Scenario: Room generation includes notable object images when backend supports multi-reference input
    Given a room contains notable objects
    And one or more notable objects have ready images
    And the selected backend supports "multi_reference"
    When a backend generation request is built for the room
    Then those notable object images are included as room reference inputs

  Scenario: Room generation falls back to text when backend does not support multi-reference input
    Given a room contains notable objects
    And one or more notable objects have ready images
    And the selected backend does not support "multi_reference"
    When a backend generation request is built for the room
    Then the object images are not passed directly as multiple image references
    And object captions, names, or descriptions are incorporated into the room prompt instead

  Scenario: Non-notable objects are excluded from room generation context
    Given a room contains many objects
    And only some of those objects are considered notable by policy
    When a backend generation request is built for the room
    Then only notable objects are included as direct image references or prompt context
    And non-notable clutter is excluded

  Scenario: Core behavior does not require a specific backend implementation
    Given the package is configured with a backend that implements the backend API
    When a generation request is processed
    Then the core Evennia integration behaves the same regardless of backend
    And backend-specific behavior is limited to capability differences and generation results

  Scenario: Unsupported backend features trigger graceful fallback
    Given the selected backend lacks a requested feature
    When a generation request is evaluated
    Then the package falls back to a supported behavior when possible
    And does not crash solely because an advanced feature is unavailable
