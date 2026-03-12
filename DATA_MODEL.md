# DATA_MODEL.md

Data Model Specification for **evennia-ai-image-generator**

---

# 1. Purpose

This document defines the data model used by `evennia-ai-image-generator`.

The data model governs:

* how image metadata is stored on Evennia rooms and objects
* how generated files are organized on disk
* how image states move through their lifecycle
* how prior images can be reused when a room or object returns to a previously seen state

The model is designed to support:

* lazy generation
* non-blocking updates
* visual continuity
* deterministic image reuse
* backend independence

---

# 2. Design Principles

## State-Based Reuse

Images should be reusable when a room or object returns to a prior effective visual state.

This means the system should not only track the current image, but also track prior generated states and their associated metadata.

---

## Separation of Current State and History

Each Evennia object should store:

* its current image metadata
* a compact history of prior image states
* a mapping from state fingerprints to prior generated images

This allows efficient reuse without requiring regeneration.

---

## Backend-Neutral Storage

The stored metadata must not depend on a specific backend implementation.

The data model records results and generation inputs, not backend internals.

---

# 3. Scope

The same model applies to both:

* rooms
* objects

In this document, “subject” means either a room or an object.

---

# 4. Evennia Attribute Storage

Each image-capable subject stores its image metadata in Evennia attributes.

Recommended top-level attributes:

```text
db.image_state
db.image_current
db.image_history
db.image_index
db.image_generation
db.image_policy
```

These are described below.

---

# 5. Image Lifecycle State

`db.image_state` stores the current lifecycle state of the subject image.

Allowed values:

```text
none
pending
ready
failed
stale
```

Meaning:

* `none`
  No image has ever been generated or assigned.

* `pending`
  A generation job has been queued or is in progress.

* `ready`
  A current image is available for display.

* `failed`
  The most recent generation attempt failed.

* `stale`
  A current image exists, but the game has requested a refresh.

---

# 6. Current Image Record

`db.image_current` stores the metadata for the currently active image.

Suggested structure:

```python
{
    "image_id": "room_76_0004",
    "path": "rooms/room_76/room_76_0004.png",
    "url": "https://yourgame.com/media/scene_images/rooms/room_76/room_76_0004.png",
    "revision": 4,
    "state_fingerprint": "2f17d9a4...",
    "prompt_fingerprint": "d81bbce1...",
    "context_fingerprint": "8b280a01...",
    "prompt": "A candlelit medieval tavern interior...",
    "negative_prompt": "blurry, distorted, extra limbs",
    "seed": 123456789,
    "model_name": "sdxl-base-1.0",
    "backend_name": "diffusers",
    "mode": "img2img",
    "source_refs": [
        {"type": "continuity", "image_id": "room_76_0003"},
        {"type": "object", "subject_key": "oak bar", "image_id": "obj_188_0002"}
    ],
    "created_at": "2026-03-11T20:00:00Z"
}
```

---

# 7. Image History

`db.image_history` stores prior image records for the subject.

This should be an ordered list, oldest to newest or newest to oldest, but the project should pick one convention and keep it consistent.

Suggested structure:

```python
[
    {
        "image_id": "room_76_0001",
        "path": "rooms/room_76/room_76_0001.png",
        "revision": 1,
        "state_fingerprint": "aa11...",
        "prompt_fingerprint": "bb22...",
        "context_fingerprint": "cc33...",
        "created_at": "2026-03-01T10:15:00Z"
    },
    {
        "image_id": "room_76_0002",
        "path": "rooms/room_76/room_76_0002.png",
        "revision": 2,
        "state_fingerprint": "dd44...",
        "prompt_fingerprint": "ee55...",
        "context_fingerprint": "ff66...",
        "created_at": "2026-03-03T14:20:00Z"
    }
]
```

History entries may be compact compared to `db.image_current`.

---

# 8. State Reuse Index

`db.image_index` maps known fingerprints to previously generated images.

This is the key structure for image recycling.

Suggested structure:

```python
{
    "2f17d9a4...": {
        "image_id": "room_76_0004",
        "path": "rooms/room_76/room_76_0004.png",
        "revision": 4
    },
    "aa11...": {
        "image_id": "room_76_0001",
        "path": "rooms/room_76/room_76_0001.png",
        "revision": 1
    }
}
```

When the subject returns to a prior state fingerprint, the system can reactivate the prior image instead of generating a new one.

---

# 9. Generation Tracking

`db.image_generation` stores operational information about the most recent or active generation request.

Suggested structure:

```python
{
    "job_id": "gen_room_76_20260311_200000",
    "requested_at": "2026-03-11T20:00:00Z",
    "requested_by": "system",
    "reason": "room_updated",
    "status": "pending",
    "requested_mode": "img2img",
    "backend_name": "diffusers",
    "error": None
}
```

If generation fails, `error` can store a concise diagnostic string.

---

# 10. Policy Storage

`db.image_policy` stores subject-level overrides.

Suggested structure:

```python
{
    "enabled": True,
    "reuse_prior_images": True,
    "max_history": 20,
    "include_as_reference": True,
    "regenerate_on_look": True,
    "style": None,
    "priority": 0
}
```

This allows builders or games to override defaults per subject.

---

# 11. Fingerprints

The system should distinguish between several fingerprints.

## State Fingerprint

Represents the effective visual state of the subject.

This is the most important fingerprint for image reuse.

It should be derived from normalized visual inputs such as:

For a room:

* room name, if visually relevant
* room description
* selected notable object identities
* selected notable object image fingerprints or states
* explicit style overrides

For an object:

* object key, if visually relevant
* object description
* style overrides
* optional parent context, if configured

If two effective visual states are equivalent, they should produce the same state fingerprint.

---

## Prompt Fingerprint

Represents the normalized prompt and negative prompt sent for generation.

This is useful for debugging and auditability, but should not be the primary reuse key.

---

## Context Fingerprint

Represents the structured pre-prompt context used by the prompt builder.

This is useful for tracing how a prompt was derived.

---

# 12. Fingerprint Normalization

To maximize image reuse, fingerprints should be based on normalized inputs.

Normalization rules should include:

* trim leading and trailing whitespace
* collapse repeated internal whitespace
* standardize line endings
* normalize ordering of selected object references
* exclude non-visual metadata
* exclude timestamps and job identifiers
* exclude transient backend state

This matters because small formatting differences should not force regeneration.

---

# 13. Reuse Flow

When a new image is requested:

```text
collect visual context
      ↓
normalize context
      ↓
compute state_fingerprint
      ↓
check db.image_index
      ↓
if match found:
    reactivate prior image
else:
    queue generation
```

Reactivation means:

* set `db.image_current` to the indexed record
* set `db.image_state = "ready"`
* do not generate a new image

---

# 14. Revision Rules

Each newly generated image gets a new revision number.

If a prior image is reused, its original revision number remains unchanged.

This is important because reuse is not a new generation.

Example:

```text
room_76_0001  generated
room_76_0002  generated
room returns to state of room_76_0001
→ current image becomes room_76_0001 again
→ no room_76_0003 is created unless a new generation actually occurs
```

---

# 15. File Layout

Generated images should be stored in a deterministic directory structure.

Suggested layout:

```text
media/
  scene_images/
    rooms/
      room_76/
        room_76_0001.png
        room_76_0002.png
    objects/
      obj_188/
        obj_188_0001.png
        obj_188_0002.png
```

Alternative layouts are possible, but the project should choose one standard default.

---

# 16. Image IDs

Each generated image should have a stable image ID.

Suggested format:

```text
room_<dbref>_<revision:04d>
obj_<dbref>_<revision:04d>
```

Examples:

```text
room_76_0001
room_76_0002
obj_188_0001
```

These IDs are internal identifiers and should not depend on filenames alone.

---

# 17. Subject Classification

The system should classify subjects as one of:

```text
room
object
```

This should be stored in the current record and used in path allocation and backend request routing.

---

# 18. Source References

Each current or historical record may store references to other images used during generation.

Suggested structure:

```python
[
    {"type": "continuity", "image_id": "room_76_0001"},
    {"type": "object", "subject_key": "crystal orb", "image_id": "obj_188_0002"},
    {"type": "style", "path": "styles/oil_painting_ref.png"}
]
```

This supports traceability and future debugging.

---

# 19. Failure Records

When generation fails, the failure should be recorded without destroying current usable image data.

Recommended behavior:

* preserve the previous `db.image_current` if one exists
* set `db.image_state` to `failed` only if there is no usable current image
* otherwise leave current image active and record the failed attempt in `db.image_generation`

This prevents a transient failure from blanking out a working image.

---

# 20. Retention Policy

History should not grow forever.

Each subject should support a configurable history limit.

Suggested default:

```text
max_history = 20
```

When trimming history:

* never delete the active current record
* do not remove indexed entries still in use
* prefer trimming the oldest unreferenced records first

Optional future behavior may include deleting old files from disk.

---

# 21. Global Reuse

Version 1 should support reuse only within the same subject.

That means:

* a room reuses its own prior images
* an object reuses its own prior images

It should not try to detect that two different rooms are visually identical and share art.

That can be a future feature if desired.

---

# 22. Main Game Trigger Model

The package should not try to infer world events on its own.

Instead, the main game may request refresh or invalidation explicitly.

Suggested operations:

```python
mark_image_stale(subject, reason="room_updated")
queue_image_generation(subject, reason="room_updated")
request_image_refresh(subject, reason="builder_command")
```

These operations update the data model, especially:

* `db.image_state`
* `db.image_generation`

and then either reuse or regenerate as appropriate.

---

# 23. Minimal Required Fields

For a minimal viable implementation, these fields are enough:

```text
db.image_state
db.image_current
db.image_history
db.image_index
```

The rest improve observability and control.

---

# 24. Example Minimal Subject Data

```python
{
    "image_state": "ready",
    "image_current": {
        "image_id": "room_76_0002",
        "path": "rooms/room_76/room_76_0002.png",
        "url": "https://yourgame.com/media/scene_images/rooms/room_76/room_76_0002.png",
        "revision": 2,
        "state_fingerprint": "dd44..."
    },
    "image_history": [
        {
            "image_id": "room_76_0001",
            "path": "rooms/room_76/room_76_0001.png",
            "revision": 1,
            "state_fingerprint": "aa11..."
        }
    ],
    "image_index": {
        "aa11...": {
            "image_id": "room_76_0001",
            "path": "rooms/room_76/room_76_0001.png",
            "revision": 1
        },
        "dd44...": {
            "image_id": "room_76_0002",
            "path": "rooms/room_76/room_76_0002.png",
            "revision": 2
        }
    }
}
```

---

# 25. Future Extensions

Possible future additions include:

* shared global image cache
* content-addressed file storage
* thumbnail derivatives
* perceptual similarity matching
* style profile registries
* image moderation metadata

These should be additive and not break the base model.

---
