Feature: Performance and polish behaviors
  In order to keep image generation responsive at scale
  As an Evennia game using evennia-ai-image-generator
  I want backend initialization, queueing, and history retention to remain efficient

  Scenario: Backend model initialization is cached across generation jobs
    Given the backend model cache is cold
    When two generation jobs are processed sequentially
    Then the backend model is initialized only once
    And subsequent jobs reuse the cached model instance

  Scenario: Backend initialization is thread-safe during concurrent startup
    Given concurrent generation workers start at the same time
    When backend initialization is attempted concurrently
    Then only one backend initialization succeeds as the active initializer
    And the remaining workers reuse the initialized backend

  Scenario: Queue deduplication prevents burst duplicates for the same subject
    Given a subject already has an active generation request
    When multiple equivalent generation requests arrive in a burst
    Then no duplicate generation request is queued
    And only one active generation request exists for that subject

  Scenario: Image history is trimmed to configured retention limits
    Given a subject has image history entries exceeding the configured limit
    When history trimming runs
    Then image history entries above the configured limit are removed
    And the newest retained entries remain available

  Scenario: Performance-related configuration options are applied
    Given the package has performance tuning options configured
    When a generation request is evaluated
    Then backend and queue behavior use configured performance options
