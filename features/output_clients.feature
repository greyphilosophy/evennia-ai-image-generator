Feature: Output behavior for telnet and preview-capable clients
  In order to support traditional MUD clients and modern link-preview clients
  As an Evennia game using evennia-ai-image-generator
  I want image output to be safe for text clients and useful for clients like Discord

  Scenario: Ready image output uses a direct image URL
    Given a subject has a ready image
    And the subject has a current direct image URL
    When a player looks at the subject
    Then the output includes the direct image URL
    And the URL points directly to the generated image resource

  Scenario: Telnet-style clients receive text output only
    Given a subject has a ready image
    When a player looks at the subject through a telnet-style client
    Then the output includes a textual image URL
    And the output does not require inline binary image rendering support

  Scenario: Preview-capable clients can use the direct image URL
    Given a subject has a ready image
    And the subject has a current direct image URL
    When the look output is delivered to a preview-capable client
    Then the output still contains a direct textual image URL
    And the URL is suitable for client-side preview or embedding

  Scenario: Pending image output is client-safe
    Given a subject image state is "pending"
    When a player looks at the subject through any supported client
    Then the output includes "Image: generating..."
    And the output remains valid plain text

  Scenario: Failed image output is client-safe
    Given a subject image state is "failed"
    And the subject has no usable current image
    When a player looks at the subject through any supported client
    Then the output may include "Image: generation failed"
    And the output remains valid plain text
