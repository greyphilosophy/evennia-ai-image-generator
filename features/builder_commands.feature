Feature: Builder commands for image management
  In order to manage generated images directly
  As a builder
  I want commands that queue generation, regeneration, clearing, and prompt inspection

  Scenario: Builder manually requests image generation for the current room
    Given a builder is located in a room with image generation enabled
    When the builder enters "imagegen here"
    Then a reuse-or-generation evaluation request is queued for the room
    And the builder receives confirmation that the request was queued

  Scenario: Builder manually requests image generation for an object
    Given a builder can target an object with image generation enabled
    When the builder enters "imagegen lantern"
    Then a reuse-or-generation evaluation request is queued for that object
    And the builder receives confirmation that the request was queued

  Scenario: Builder requests regeneration for a subject
    Given a subject has image generation enabled
    When the builder enters "imageregen lantern"
    Then the subject is evaluated for reuse or new generation according to policy
    And the builder receives confirmation that the request was queued

  Scenario: Builder clears the current image
    Given a subject has a current image
    When the builder enters "imageclear lantern"
    Then the current image is removed or deactivated according to project policy
    And the subject image state becomes "none" or "stale" according to configuration

  Scenario: Builder views the effective prompt for a subject
    Given a subject has image generation enabled
    When the builder enters "imageprompt lantern"
    Then the builder is shown the effective prompt data or last stored prompt according to availability
