Feature: Look pipeline for image-enabled rooms and objects
  In order to provide images without blocking gameplay
  As an Evennia game using evennia-ai-image-generator
  I want look output to reflect current image state correctly

  Scenario: Player looks at a room with a ready image
    Given image generation is enabled for the room
    And the room image state is "ready"
    And the room has a current image URL
    When a player looks at the room
    Then the room description is shown
    And the image URL is included in the output
    And no new generation request is queued

  Scenario: Player looks at an object with a ready image
    Given image generation is enabled for the object
    And the object image state is "ready"
    And the object has a current image URL
    When a player looks at the object
    Then the object description is shown
    And the image URL is included in the output
    And no new generation request is queued

  Scenario: Player looks at a room with no image
    Given image generation is enabled for the room
    And the room image state is "none"
    And the room has no current image record
    When a player looks at the room
    Then the room description is shown
    And the output includes "Image: generating..."
    And a generation request is queued
    And the room image state becomes "pending"

  Scenario: Player looks at an object with no image
    Given image generation is enabled for the object
    And the object image state is "none"
    And the object has no current image record
    When a player looks at the object
    Then the object description is shown
    And the output includes "Image: generating..."
    And a generation request is queued
    And the object image state becomes "pending"

  Scenario: Player looks at a room while generation is pending
    Given image generation is enabled for the room
    And the room image state is "pending"
    When a player looks at the room
    Then the room description is shown
    And the output includes "Image: generating..."
    And no duplicate generation request is queued

  Scenario: Multiple players look at the same room while generation is pending
    Given image generation is enabled for the room
    And the room image state is "pending"
    When multiple players look at the room before generation completes
    Then each player sees the room description
    And each player sees "Image: generating..."
    And only one active generation request exists for that room

  Scenario: Player looks at a subject with image generation disabled
    Given image generation is disabled for the subject
    When a player looks at the subject
    Then the normal text description is shown
    And no image generation request is queued
    And no image status line is required
