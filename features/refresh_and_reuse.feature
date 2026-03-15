Feature: Refresh and reuse of prior images
  In order to avoid unnecessary regeneration
  As an Evennia game using evennia-ai-image-generator
  I want prior images to be reused when a subject returns to a prior visual state

  Scenario: Main game marks a room image as stale
    Given a room has a current image
    When the main game marks the room image as stale with reason "room_updated"
    Then the room image state becomes "stale"
    And the reason is recorded in generation metadata if configured

  Scenario: Main game requests refresh for an object
    Given image generation is enabled for the object
    When the main game requests image refresh for the object with reason "builder_update"
    Then reuse or generation evaluation is queued
    And the object is not regenerated synchronously in the caller flow

  Scenario: Main game requests refresh for a disabled subject
    Given image generation is disabled for the subject
    When the main game requests image refresh for that subject
    Then the request is ignored or rejected according to project policy
    And no backend generation occurs

  Scenario: Room refresh reuses a prior image when state matches
    Given image generation is enabled for the room
    And the room image index contains a previously stored state fingerprint
    And the current normalized visual state matches that fingerprint
    When the main game requests image refresh for the room
    Then the previously stored image is reactivated
    And the room image state becomes "ready"
    And no new backend generation occurs

  Scenario: Object refresh reuses a prior image when state matches
    Given image generation is enabled for the object
    And the object image index contains a previously stored state fingerprint
    And the current normalized visual state matches that fingerprint
    When the main game requests image refresh for the object
    Then the previously stored image is reactivated
    And the object image state becomes "ready"
    And no new backend generation occurs

  Scenario: Room refresh queues generation when no reusable prior state exists
    Given image generation is enabled for the room
    And the room has no indexed image for the current visual state
    When the main game requests image refresh for the room
    Then the room image state becomes "stale" or "pending" according to policy
    And a generation request is queued

  Scenario: Equivalent visual states match despite irrelevant formatting differences
    Given a subject has a previously indexed image for a normalized visual state
    And the current visual data differs only by non-visual formatting differences
    When a refresh evaluation occurs
    Then the state fingerprint matches the previously indexed state
    And the prior image is eligible for reuse

  Scenario: Different visual states do not match
    Given a subject has a previously indexed image
    And the current normalized visual state differs in visually meaningful ways
    When a refresh evaluation occurs
    Then the state fingerprint does not match the indexed prior state
    And a new generation request may be queued

  Scenario: Reuse updates current metadata without creating a new revision
    Given a subject matches a previously known state
    When the prior image is reactivated
    Then the current image record points to the reused image
    And no new generated image file is required
    And no new revision number is created solely because of reuse
