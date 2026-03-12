# IMPLEMENTATION_PLAN.md

Implementation Plan for **evennia-ai-image-generator**

---

# 1. Purpose

This document defines the staged implementation plan for `evennia-ai-image-generator`.

The goal is to implement the system in small, testable phases that progressively satisfy the behaviors defined in `BEHAVIOR_SPEC.md`.

Each phase should produce a working system that can be validated before proceeding.

---

# 2. Implementation Philosophy

The implementation follows several principles.

### Vertical slices

Each phase implements a complete behavior slice from the BDD spec rather than partial infrastructure.

### Early usability

The system should become usable in a minimal form early in development.

### Expandable architecture

Later phases extend the system without breaking earlier functionality.

---

# 3. Phase Overview

The implementation is divided into the following phases:

```
Phase 1 — Core integration
Phase 2 — Image lifecycle state model
Phase 3 — Generation queue
Phase 4 — Backend adapter system
Phase 5 — Prompt and context pipeline
Phase 6 — Image reuse system
Phase 7 — Reference-aware scene generation
Phase 8 — Builder commands
Phase 9 — Failure handling and robustness
Phase 10 — Performance and polish
```

---

# 4. Phase 1 — Core Integration

## Goal

Allow rooms and objects to display image URLs.

No AI generation yet.

## Implement

SceneImageMixin skeleton

Attributes:

```
image_state
image_current
```

Modify appearance output.

Behavior:

```
If image_state == ready
    show image URL
Else
    show nothing
```

## Validates behaviors

* Viewing a subject with a ready image
* Disabled image generation

---

# 5. Phase 2 — Image Lifecycle State Model

## Goal

Implement the image state machine.

States:

```
none
pending
ready
failed
stale
```

## Implement

State transitions.

```
none → pending
pending → ready
pending → failed
ready → stale
stale → pending
```

Add metadata fields defined in `DATA_MODEL.md`.

## Validates behaviors

* Viewing a subject with no image
* Viewing a subject with a ready image
* Viewing a subject after failure

---

# 6. Phase 3 — Generation Queue

## Goal

Introduce asynchronous generation.

## Implement

Queue function:

```
queue_image_generation(subject)
```

Generation worker:

```
process_generation_job(subject)
```

Temporary placeholder generator:

```
generate_placeholder_image()
```

Placeholder behavior ensures the system works without an AI backend yet.

## Validates behaviors

* Missing image queues generation
* Pending generation behavior
* No duplicate jobs

---

# 7. Phase 4 — Backend Adapter System

## Goal

Introduce the backend interface defined in `BACKEND_API.md`.

## Implement

Classes:

```
BaseImageBackend
DiffusersBackend (initial implementation)
```

Backend loader:

```
load_backend()
```

Generation worker updated to use backend.

## Validates behaviors

* Backend independence
* Basic txt2img generation

---

# 8. Phase 5 — Prompt and Context Pipeline

## Goal

Convert room/object data into generation prompts.

## Implement

Context collector:

```
collect_subject_context(subject)
```

Prompt builder:

```
build_prompt(context)
```

Negative prompt defaults.

Add prompt fingerprints.

## Validates behaviors

* Prompt inspection via builder command
* Deterministic prompt generation

---

# 9. Phase 6 — Image Reuse System

## Goal

Implement state fingerprinting and reuse.

## Implement

Fingerprint generation:

```
compute_state_fingerprint(subject)
```

Image index lookup:

```
find_reusable_image(fingerprint)
```

Reuse flow:

```
if reusable image exists
    reactivate image
else
    generate new image
```

## Validates behaviors

* Reuse of prior image states
* Avoiding unnecessary generation

---

# 10. Phase 7 — Reference-Aware Scene Generation

## Goal

Allow room generation to incorporate object context.

## Implement

Notable object selection:

```
select_notable_objects(room)
```

Reference gathering:

```
collect_reference_images(room)
```

Backend capability fallback.

```
if backend supports multi_reference
    pass image references
else
    convert references to text
```

## Validates behaviors

* Object reference behavior
* Backend capability fallback

---

# 11. Phase 8 — Builder Commands

## Goal

Expose manual controls.

## Commands

```
imagegen
imageregen
imageclear
imageprompt
```

## Implement

Command handlers.

Command permissions for builders.

## Validates behaviors

* Builder command scenarios

---

# 12. Phase 9 — Failure Handling

## Goal

Improve robustness.

## Implement

Exception types:

```
ImageGenerationError
BackendConfigurationError
ModelLoadError
```

Failure metadata recording.

Failure-safe fallback behavior.

## Validates behaviors

* Generation failure behavior
* Preserving usable images

---

# 13. Phase 10 — Performance and Polish

## Goal

Improve stability and performance.

## Improvements

Model caching.

Thread-safe backend initialization.

Queue deduplication improvements.

History trimming.

Configuration options.

---

# 14. Milestone Targets

## Milestone 1

Minimal system with generation.

```
Phases 1–4
```

Capabilities:

* generate images
* show URLs
* async behavior

---

## Milestone 2

Reusable and stable system.

```
Phases 1–6
```

Capabilities:

* image reuse
* prompt control
* backend abstraction

---

## Milestone 3

Feature complete version 1.

```
Phases 1–9
```

Capabilities:

* reference-aware scenes
* builder tools
* robust error handling

---

# 15. Suggested Development Order

Recommended file implementation order:

```
mixins.py
data_model.py
queue.py
backend/base.py
backend/diffusers_backend.py
context.py
prompts.py
reuse.py
commands/
```

This order minimizes circular dependencies.

---

# 16. Minimal Viable Implementation

The smallest useful version includes:

```
SceneImageMixin
Generation queue
Diffusers backend
Prompt builder
```

Reuse and references can be added later without breaking compatibility.

---

# 17. Testing Strategy

Testing should follow the BDD scenarios.

Initial tests should cover:

```
look pipeline
pending generation behavior
successful generation flow
reuse flow
failure flow
```

Automated testing tools may include:

```
pytest
pytest-bdd
behave
```

---

# 18. Future Extensions

Possible future improvements include:

* ControlNet support
* inpainting updates
* scene graph generation
* object placement hints
* deterministic style profiles
* distributed generation workers

---
