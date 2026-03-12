# BEHAVIOR_SPEC.md

Behavior Specification for **evennia-ai-image-generator**

---

# 1. Purpose

This document defines the expected external behavior of `evennia-ai-image-generator` using a behavior-driven development style.

The goal is to describe what the system does from the perspective of:

* players
* builders
* the main game
* backend integrations

These scenarios describe observable behavior and acceptance criteria. They are intended to guide implementation and later automated tests.

---

# 2. Scope

This document covers:

* look behavior for rooms and objects
* image generation and reuse
* regeneration requests from the main game
* reference-aware scene generation
* backend capability fallback
* builder commands
* error handling

This document does not define internal implementation details unless they affect observable behavior.

---

# 3. Terms

## Subject

A subject is either:

* a room
* an object

## Current Image

The currently active image record for a subject.

## Prior State

A previously known visual state of a subject that has already had an image generated.

## Reuse

Reactivating a previously generated image for a subject instead of generating a new one.

## Generation Request

A queued request to evaluate whether a subject should reuse an old image or generate a new one.

---

# 4. Feature: Viewing a subject with a ready image

## Scenario: Player looks at a room with a ready image

**Given** a room has image generation enabled
**And** the room image state is `ready`
**And** the room has a current image URL
**When** a player uses `look` on the room
**Then** the room description is shown
**And** the image URL is included in the output
**And** no new generation request is queued

## Scenario: Player looks at an object with a ready image

**Given** an object has image generation enabled
**And** the object image state is `ready`
**And** the object has a current image URL
**When** a player uses `look` on the object
**Then** the object description is shown
**And** the image URL is included in the output
**And** no new generation request is queued

---

# 5. Feature: Viewing a subject with no current image

## Scenario: Player looks at a room with no image

**Given** a room has image generation enabled
**And** the room image state is `none`
**And** the room has no current image record
**When** a player uses `look` on the room
**Then** the room description is shown
**And** the output includes `Image: generating...`
**And** a generation request is queued
**And** the room image state becomes `pending`

## Scenario: Player looks at an object with no image

**Given** an object has image generation enabled
**And** the object image state is `none`
**And** the object has no current image record
**When** a player uses `look` on the object
**Then** the object description is shown
**And** the output includes `Image: generating...`
**And** a generation request is queued
**And** the object image state becomes `pending`

---

# 6. Feature: Viewing a subject while generation is pending

## Scenario: Player looks at a room while image generation is already pending

**Given** a room has image generation enabled
**And** the room image state is `pending`
**When** a player uses `look` on the room
**Then** the room description is shown
**And** the output includes `Image: generating...`
**And** no duplicate generation request is queued

## Scenario: Multiple players look at the same room while generation is pending

**Given** a room has image generation enabled
**And** the room image state is `pending`
**When** multiple players use `look` on the room before generation completes
**Then** each player sees the room description
**And** each player sees `Image: generating...`
**And** only one active generation request exists for that room

---

# 7. Feature: Viewing a subject after generation failure

## Scenario: Player looks at a room whose initial image generation failed

**Given** a room has image generation enabled
**And** the room image state is `failed`
**And** the room has no usable current image
**When** a player uses `look` on the room
**Then** the room description is shown
**And** the output may include `Image: generation failed`

## Scenario: Player looks at a room with a usable image after a failed refresh

**Given** a room has image generation enabled
**And** the room has a usable current image
**And** the most recent refresh attempt failed
**When** a player uses `look` on the room
**Then** the room description is shown
**And** the current image URL is included in the output
**And** the failed refresh does not remove the usable image from display

---

# 8. Feature: Completing background generation

## Scenario: Background generation completes successfully for a room

**Given** a room image state is `pending`
**And** a valid generation request exists for the room
**When** the backend completes image generation successfully
**Then** the room image state becomes `ready`
**And** the room current image record is stored
**And** the room current image URL is available for future `look` output

## Scenario: Background generation completes successfully for an object

**Given** an object image state is `pending`
**And** a valid generation request exists for the object
**When** the backend completes image generation successfully
**Then** the object image state becomes `ready`
**And** the object current image record is stored
**And** the object current image URL is available for future `look` output

---

# 9. Feature: Reusing a prior image instead of generating a new one

## Scenario: Main game requests refresh and the room matches a prior known state

**Given** a room has image generation enabled
**And** the room image index contains a previously stored state fingerprint
**And** the current normalized visual state matches that fingerprint
**When** the main game requests image refresh for the room
**Then** the previously stored image is reactivated
**And** the room image state becomes `ready`
**And** no new backend generation occurs

## Scenario: Main game requests refresh and the object matches a prior known state

**Given** an object has image generation enabled
**And** the object image index contains a previously stored state fingerprint
**And** the current normalized visual state matches that fingerprint
**When** the main game requests image refresh for the object
**Then** the previously stored image is reactivated
**And** the object image state becomes `ready`
**And** no new backend generation occurs

---

# 10. Feature: Generating a new image when no reusable prior state exists

## Scenario: Main game requests refresh and no prior room state matches

**Given** a room has image generation enabled
**And** the room has no indexed image for the current visual state
**When** the main game requests image refresh for the room
**Then** the room image state becomes `stale` or `pending` according to policy
**And** a generation request is queued

## Scenario: Main game requests refresh and no prior object state matches

**Given** an object has image generation enabled
**And** the object has no indexed image for the current visual state
**When** the main game requests image refresh for the object
**Then** the object image state becomes `stale` or `pending` according to policy
**And** a generation request is queued

---

# 11. Feature: Main game controls regeneration explicitly

## Scenario: The package does not infer world events by itself

**Given** a room changes in the main game
**And** the main game does not request image refresh
**When** a player uses `look` on the room
**Then** the package does not independently infer a world event occurred
**And** image refresh behavior follows only the current stored image state and policy

## Scenario: Main game marks a room image as stale

**Given** a room has a current image
**When** the main game marks the room image as stale with reason `room_updated`
**Then** the room image state becomes `stale`
**And** the reason is recorded in generation metadata if configured

## Scenario: Main game queues an object refresh directly

**Given** an object has image generation enabled
**When** the main game requests image refresh for the object with reason `builder_update`
**Then** reuse or generation evaluation is queued
**And** the object is not regenerated synchronously in the caller’s execution flow

---

# 12. Feature: Using continuity references during regeneration

## Scenario: Room refresh uses prior room image when backend supports img2img

**Given** a room has a current image
**And** the selected backend supports `img2img`
**When** a new backend generation request is built for the room
**Then** the prior room image is included as a continuity reference

## Scenario: Object refresh uses prior object image when backend supports img2img

**Given** an object has a current image
**And** the selected backend supports `img2img`
**When** a new backend generation request is built for the object
**Then** the prior object image is included as a continuity reference

## Scenario: Continuity falls back when img2img is unavailable

**Given** a subject has a current image
**And** the selected backend does not support `img2img`
**When** a new backend generation request is built
**Then** the system falls back to a supported mode
**And** the request still reflects the current textual state of the subject

---

# 13. Feature: Using object references in room generation

## Scenario: Room generation includes notable object images when backend supports multi-reference input

**Given** a room contains notable objects
**And** one or more notable objects have ready images
**And** the selected backend supports multi-reference image input
**When** a backend generation request is built for the room
**Then** those notable object images are included as room reference inputs

## Scenario: Room generation falls back to text when backend does not support multi-reference input

**Given** a room contains notable objects
**And** one or more notable objects have ready images
**And** the selected backend does not support multi-reference image input
**When** a backend generation request is built for the room
**Then** the object images are not passed directly as multiple image references
**And** object captions, names, or descriptions are incorporated into the room prompt instead

## Scenario: Non-notable objects are excluded from room generation context

**Given** a room contains many objects
**And** only some of those objects are considered notable by policy
**When** a backend generation request is built for the room
**Then** only notable objects are included as direct image references or prompt context
**And** non-notable clutter is excluded

---

# 14. Feature: Deduplicating generation work

## Scenario: Repeated refresh requests do not create duplicate active jobs

**Given** a subject already has an active generation request
**When** another equivalent refresh request is made before the first completes
**Then** the system does not queue a duplicate active generation job for that subject

## Scenario: Repeated looks do not create duplicate jobs

**Given** a subject image state is `pending`
**When** players repeatedly look at the subject
**Then** the system does not queue additional duplicate generation requests

---

# 15. Feature: Builder command behavior

## Scenario: Builder manually requests image generation for the current room

**Given** a builder is located in a room with image generation enabled
**When** the builder uses `imagegen here`
**Then** a reuse-or-generation evaluation request is queued for the room
**And** the builder receives confirmation that the request was queued

## Scenario: Builder manually requests image generation for an object

**Given** a builder can target an object with image generation enabled
**When** the builder uses `imagegen <object>`
**Then** a reuse-or-generation evaluation request is queued for that object
**And** the builder receives confirmation that the request was queued

## Scenario: Builder requests regeneration for a subject

**Given** a subject has image generation enabled
**When** the builder uses `imageregen <subject>`
**Then** the subject is evaluated for reuse or new generation according to policy
**And** the builder receives confirmation that the request was queued

## Scenario: Builder clears the current image

**Given** a subject has a current image
**When** the builder uses `imageclear <subject>`
**Then** the current image is removed or deactivated according to project policy
**And** the subject image state becomes `none` or `stale` according to configuration

## Scenario: Builder views the effective prompt for a subject

**Given** a subject has image generation enabled
**When** the builder uses `imageprompt <subject>`
**Then** the builder is shown the effective prompt data or last stored prompt according to availability

---

# 16. Feature: Disabled image generation

## Scenario: Player looks at a subject with image generation disabled

**Given** a subject has image generation disabled
**When** a player uses `look` on the subject
**Then** the normal text description is shown
**And** no image generation request is queued
**And** no image status line is required

## Scenario: Main game requests refresh for a disabled subject

**Given** a subject has image generation disabled
**When** the main game requests image refresh for that subject
**Then** the request is ignored or rejected according to project policy
**And** no backend generation occurs

---

# 17. Feature: Failure handling

## Scenario: Initial generation fails for a subject with no usable image

**Given** a subject has no usable current image
**And** a generation request is being processed
**When** backend generation fails
**Then** the subject image state becomes `failed`
**And** the failure is recorded in generation metadata if configured

## Scenario: Refresh generation fails for a subject with a usable current image

**Given** a subject has a usable current image
**And** a refresh generation request is being processed
**When** backend generation fails
**Then** the existing current image remains active
**And** the failure is recorded in generation metadata if configured
**And** the subject does not lose its visible image URL

---

# 18. Feature: File and metadata persistence

## Scenario: Successful generation updates subject metadata

**Given** a subject has a pending generation request
**When** generation succeeds
**Then** the current image record is stored on the subject
**And** the image history is updated
**And** the image index is updated with the subject’s state fingerprint

## Scenario: Reuse updates current metadata without creating a new revision

**Given** a subject matches a previously known state
**When** the prior image is reactivated
**Then** the current image record points to the reused image
**And** no new generated image file is required
**And** no new revision number is created solely because of reuse

---

# 19. Feature: Normalized state matching

## Scenario: Equivalent visual states match despite irrelevant formatting differences

**Given** a subject has a previously indexed image for a normalized visual state
**And** the subject’s current visual data differs only by non-visual formatting differences
**When** a refresh evaluation occurs
**Then** the state fingerprint matches the previously indexed state
**And** the prior image is eligible for reuse

## Scenario: Different visual states do not match

**Given** a subject has a previously indexed image
**And** the current normalized visual state differs in visually meaningful ways
**When** a refresh evaluation occurs
**Then** the state fingerprint does not match the indexed prior state
**And** a new generation request may be queued

---

# 20. Feature: Backend independence

## Scenario: Core behavior does not require a specific backend implementation

**Given** the package is configured with a backend that implements the backend API
**When** a generation request is processed
**Then** the core Evennia integration behaves the same regardless of backend
**And** backend-specific behavior is limited to capability differences and generation results

## Scenario: Unsupported backend features trigger graceful fallback

**Given** the selected backend lacks a requested feature
**When** a generation request is evaluated
**Then** the package falls back to a supported behavior when possible
**And** does not crash solely because an advanced feature is unavailable

---

# 21. Feature: Output expectations for telnet and Discord-style clients

## Scenario: Image output is link-based rather than inline binary image data

**Given** a subject has a ready image
**When** a player uses `look` through a telnet-style client
**Then** the output includes a textual image URL
**And** the package does not require inline image rendering support from the client

## Scenario: Direct image URLs are suitable for external previewing clients

**Given** a subject has a ready image
**When** the output is viewed through a client that can preview direct image links
**Then** the included URL points directly to the generated image resource

---

# 22. Feature: Minimal acceptance behavior for version 1

## Scenario: Version 1 room flow

**Given** a room has image generation enabled
**When** a player looks at the room for the first time
**Then** the room description is shown
**And** the room image generation is queued
**And** a later look shows a direct image URL after success

## Scenario: Version 1 object flow

**Given** an object has image generation enabled
**When** a player looks at the object for the first time
**Then** the object description is shown
**And** the object image generation is queued
**And** a later look shows a direct image URL after success

## Scenario: Version 1 reuse flow

**Given** a subject has a previously indexed image for a prior state
**When** the subject returns to that state and refresh is requested
**Then** the subject reuses the prior image instead of generating a new one

---

# 23. Acceptance Notes

The following are considered core acceptance criteria for the first implementation:

* `look` never blocks on image generation
* existing ready images are shown immediately
* missing images queue background work
* pending work is not duplicated
* prior images can be reused for matching prior states
* backend failures do not destroy usable current images
* room generation can use object context directly or through textual fallback
* the main game explicitly decides when refresh is needed

---

# 24. Suggested Future Conversion to Automated Tests

This document is intended to be convertible into automated BDD scenarios.

Possible future test organization:

```text
features/
  look_pipeline.feature
  reuse.feature
  refresh_requests.feature
  backend_fallback.feature
  builder_commands.feature
  failure_handling.feature
```

Possible tooling:

* `pytest-bdd`
* `behave`

---
