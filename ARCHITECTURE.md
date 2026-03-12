# ARCHITECTURE.md

Architecture Overview for **evennia-ai-image-generator**

---

# 1. Purpose

`evennia-ai-image-generator` provides automatic AI-generated images for rooms and objects in an Evennia MUD.

The system integrates with the Evennia appearance pipeline and generates images lazily when players view objects using the `look` command.

Images are generated locally using Stable Diffusion–compatible pipelines and exposed through HTTP URLs so clients such as Discord can embed previews.

The system is designed to be:

* non-blocking
* backend-agnostic
* reusable across Evennia games
* visually consistent over time

---

# 2. Design Principles

### Lazy Generation

Images are only generated when needed.
If an image does not exist when an object is viewed, generation is queued in the background.

This prevents large initial compute costs when a world is created.

---

### Non-Blocking Gameplay

Image generation must never block gameplay.

All generation tasks are executed asynchronously using background workers or thread pools.

Players immediately receive the room description even while images are still being generated.

---

### Visual Continuity

When rooms or objects change, previously generated images are used as references.

This reduces visual drift and keeps locations recognizable over time.

---

### Backend Abstraction

The system separates **Evennia integration** from **image generation**.

Image backends implement a simple interface so different AI pipelines can be used.

Supported examples:

* Stable Diffusion via Diffusers
* ComfyUI workflows
* remote inference servers

---

### Reference-Aware Scene Generation

Room images may incorporate visual information from objects in the room.

If an object already has an image, it can be used as a reference during room generation.

---

# 3. High-Level System Diagram

```
Player Command
      │
      ▼
look / examine
      │
      ▼
SceneImageMixin
      │
      ▼
Image Context Collector
      │
      ▼
Prompt Builder
      │
      ▼
ImageGenerationRequest
      │
      ▼
Backend Adapter
      │
      ▼
Diffusion Model
      │
      ▼
Image File Storage
      │
      ▼
URL returned in appearance text
```

---

# 4. Core Components

## SceneImageMixin

The primary integration point with Evennia.

Responsibilities:

* Detect when images are missing
* Queue image generation
* Append image URLs to appearance text
* Maintain metadata for rooms and objects

The mixin can be added to any Evennia typeclass.

Example:

```python
class Room(SceneImageMixin, DefaultRoom):
    pass
```

---

## Image Context Collector

Collects relevant information for image generation.

For rooms this includes:

* room name
* room description
* notable objects
* prior room image
* object images

For objects this includes:

* object name
* object description
* prior object image
* optional room context

---

## Prompt Builder

Transforms collected context into a visual prompt.

Responsibilities:

* convert structured data into prompt text
* apply style templates
* enforce prompt limits
* produce positive and negative prompts

Example prompt:

```
A fantasy illustration of a candlelit tavern interior.
Wooden tables, stone fireplace, dim lighting.
Objects present: iron chandelier, oak bar counter.
Atmosphere: warm, medieval, detailed environment art.
```

---

## ImageGenerationRequest

The central data structure describing a generation task.

Example:

```python
@dataclass
class ImageGenerationRequest:
    subject_type: Literal["room", "object"]
    subject_key: str
    prompt: str
    negative_prompt: str
    mode: Literal["txt2img", "img2img"]
    reference_images: list[ReferenceImage]
```

This structure allows the system to support multiple backend pipelines.

---

## Backend Adapter

Backends translate `ImageGenerationRequest` into model-specific operations.

All backends implement a common interface.

Example methods:

```
generate(request)
supports_feature(feature_name)
```

Backends may support different capabilities such as:

* text-to-image
* image-to-image
* multi-image composition
* inpainting

---

## Async Job Queue

Generation jobs are queued so they do not block gameplay.

Typical workflow:

```
look command
   ↓
detect missing image
   ↓
enqueue generation job
   ↓
background worker generates image
   ↓
store result
```

Evennia's deferred threading system or a task queue can be used.

---

## Image Storage

Generated images are stored locally.

Example directory layout:

```
media/
  scene_images/
      rooms/
      objects/
```

Images are versioned to support continuity.

Example:

```
tavern_v1.png
tavern_v2.png
```

Metadata is stored on the Evennia object.

---

# 5. Image Generation Modes

## txt2img

Used when no prior image exists.

Inputs:

* textual prompt
* optional reference images

---

## img2img

Used when updating an existing object or room.

Inputs:

* prior image
* updated prompt

Purpose:

Maintain visual continuity while applying changes.

---

## compose (future)

Used when constructing rooms from multiple object references.

Inputs:

* multiple object images
* scene prompt

---

# 6. Object Selection for Room Scenes

Not all objects in a room should be included in image generation.

The system selects **notable objects** using rules such as:

* objects flagged as notable
* objects with images already generated
* objects marked as large or prominent
* builder-defined priority

Typical limits:

```
3–6 objects per scene
```

This prevents overcrowded images.

---

# 7. Image Metadata

Each image-capable object stores metadata.

```
db.image_state
db.image_url
db.image_path
db.image_prompt
db.image_negative_prompt
db.image_seed
db.image_model
db.image_generated_ts
db.image_revision
db.image_source_refs
db.previous_image_path
```

This enables regeneration and continuity.

---

# 8. Image Lifecycle

### Initial Creation

```
look command
      ↓
no image exists
      ↓
generation queued
      ↓
image created
      ↓
image URL stored
```

---

### Object Update

```
object description changes
      ↓
existing image detected
      ↓
img2img refinement
      ↓
new version stored
```

---

### Room Update

```
room changes
      ↓
prior room image used
      ↓
refinement generation
```

---

# 9. Performance Considerations

Image generation is expensive.

Best practices include:

lazy generation
limiting reference objects
GPU acceleration
background workers

---

# 10. Extensibility

Developers can extend the system with custom backends.

Examples:

* alternative diffusion models
* procedural renderers
* remote generation services

The backend interface isolates these systems from the Evennia integration layer.

---

# 11. Security Considerations

If images are exposed over HTTP:

* ensure generated paths are sanitized
* restrict filesystem access
* validate prompts if user-editable

---

# 12. Future Improvements

Potential future enhancements:

* inpainting updates
* region-based room updates
* deterministic scene seeds
* object placement hints
* persistent scene graphs
* style profiles

---
