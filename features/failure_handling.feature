Feature: Failure handling and persistence
  In order to keep the game usable when generation fails
  As an Evennia game using evennia-ai-image-generator
  I want failures to be visible, safe, and non-destructive

  Scenario: Initial generation fails for a room with no usable image
    Given a room has image generation enabled
    And the room has no usable current image
    And a generation request is being processed
    When backend generation fails
    Then the room image state becomes "failed"
    And the failure is recorded in generation metadata if configured

  Scenario: Refresh generation fails for a subject with a usable current image
    Given a subject has a usable current image
    And a refresh generation request is being processed
    When backend generation fails
    Then the existing current image remains active
    And the failure is recorded in generation metadata if configured
    And the subject does not lose its visible image URL

  Scenario: Player looks at a room whose initial image generation failed
    Given a room has image generation enabled
    And the room image state is "failed"
    And the room has no usable current image
    When a player looks at the room
    Then the room description is shown
    And the output may include "Image: generation failed"

  Scenario: Successful generation updates subject metadata
    Given a subject has a pending generation request
    When generation succeeds
    Then the current image record is stored on the subject
    And the image history is updated
    And the image index is updated with the subject state fingerprint

  Scenario: Background generation completes successfully for a room
    Given a room image state is "pending"
    And a valid generation request exists for the room
    When the backend completes image generation successfully
    Then the room image state becomes "ready"
    And the room current image record is stored
    And the room current image URL is available for future look output

  Scenario: Repeated refresh requests do not create duplicate active jobs
    Given a subject already has an active generation request
    When another equivalent refresh request is made before the first completes
    Then the system does not queue a duplicate active generation job for that subject
