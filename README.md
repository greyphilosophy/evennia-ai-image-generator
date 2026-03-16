# README.md

## evennia-ai-image-generator

AI-generated images for rooms and objects in Evennia MUDs.

`evennia-ai-image-generator` automatically generates and maintains images for rooms and objects when players examine them. Images are created locally using Stable Diffusion–compatible pipelines and returned as URLs that can be embedded by modern clients such as Discord.

The system is asynchronous, backend-agnostic, and designed to integrate cleanly with existing Evennia games.

---

# Features

Automatic image generation
Images are generated the first time a room or object is viewed.

State-based image reuse
If a room or object returns to a previously seen visual state, the system reuses an earlier image instead of generating a new one.

Local AI generation
Images are generated locally using Stable Diffusion compatible backends.

Visual continuity
When rooms or objects change, prior images may be used as references to maintain consistent appearance.

Reference-aware scenes
Room images may incorporate images of notable objects present in the room.

Async operation
Image generation never blocks gameplay.

Reusable architecture
The system is designed to work with any Evennia game.

---

# Example Output

```
A dimly lit tavern filled with the smell of smoke and spilled ale.

Image: https://yourgame.com/media/scene_images/rooms/room_76/room_76_0002.png
```

When viewed through Discord, the image link is automatically embedded.

---

# Installation

`evennia-ai-image-generator` is not currently published on PyPI as an installable wheel/sdist,
so `pip install evennia-ai-image-generator` will fail.

For now, install from source by vendoring the package into your Evennia project:

1. Copy the `evennia_ai_image_generator/` folder from this repository into your game codebase
   (or otherwise make it importable on your `PYTHONPATH`).
2. Add the package to your Evennia settings.
3. Run migrations.

### Option B: vendor directly into your game repo

Copy only the package directory into your game project:

```text
from: C:\MUD\evennia-ai-image-generator\evennia_ai_image_generator
to:   C:\MUD\aicompany_mud\evennia_ai_image_generator
```

This avoids `PYTHONPATH` changes but means you must recopy updates when this repo changes.

After either option:

1. Add the package to your Evennia settings.
2. Run migrations.

Add the package to your Evennia settings:

```python
INSTALLED_APPS += ["evennia_ai_image_generator"]
```

Enable the image mixin in your typeclasses:

```python
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia import DefaultRoom

class Room(SceneImageMixin, DefaultRoom):
    pass
```

Run migrations if needed:

```bash
evennia migrate
```

---

# How It Works

When a player examines a room or object:

1. The system checks whether an image already exists.

2. If an image exists
   The stored image URL is displayed.

3. If no image exists
   A background generation job is queued.

4. The player sees:

```
Image: generating...
```

Once generation finishes, future views will display the image.

If the subject later returns to a previously known visual state, the system may reuse an earlier generated image.

---

# Supported Backends

Planned backends include:

Diffusers
Embedded Stable Diffusion pipelines.

ComfyUI
External workflow-based generation server.

Additional backends can be added by implementing the backend API.


### Diffusers test setup

You can use the built-in diffusers backend:

```python
IMAGE_BACKEND = {
    "backend": "diffusers",
    "options": {
        "model_id": "runwayml/stable-diffusion-v1-5",
        "device": "cpu",
        "dry_run": True,
        "shared_model_cache": True,
    },
}
```

Set `shared_model_cache=False` if you need strict per-worker model isolation instead of process-wide cache reuse.

You can also resolve runtime services from one config dictionary:

```python
from evennia_ai_image_generator import build_runtime_services

services = build_runtime_services({
    "backend": {
        "backend": "diffusers",
        "options": {"dry_run": True, "shared_model_cache": False},
    },
    "queue": {"max_pending": 10},
    "max_image_history": 25,
})
```


Recommended open-source models:

* `runwayml/stable-diffusion-v1-5` (default recommendation; strong quality/speed tradeoff for SD1.5)
* `hf-internal-testing/tiny-stable-diffusion-pipe` (very small, ideal for CI/tests only)

Default backend target is SD1.5 (`runwayml/stable-diffusion-v1-5`). For CI or smoke tests, temporarily switch to the tiny model with `dry_run=True`.

### Multimodal LLMs vs Diffusion backends

Short answer: multimodal LLMs are useful here, but mostly for *analysis/planning* rather than final image synthesis.

- Multimodal LLMs (vision-language models) are excellent for:
  - generating/refining prompts
  - inspecting generated images for consistency
  - selecting notable objects/context from room state
- Diffusion/image-generation models are still the most practical local option for producing final PNG outputs.

Recommended hybrid approach:

1. Keep diffusion as the image renderer (`backend: "diffusers"`).
2. Optionally add an LLM pre-step to build better prompts/context.
3. Use `runwayml/stable-diffusion-v1-5` as the primary renderer.
4. Use `hf-internal-testing/tiny-stable-diffusion-pipe` only for fast CI wiring checks.

Important nuance: `img2txt -> txt2img` is **not** equivalent to true `img2img`.

- `img2txt` compresses an image into text and loses geometry, texture, and latent detail.
- true `img2img` conditions directly on image pixels/latents, preserving composition and style much better.
- this package now applies an explicit continuity/style text hint fallback when a subject has a prior image but the backend lacks `img2img`.

---

# Regeneration Control

The image generator does not attempt to detect world events on its own.

Instead, the main game can explicitly request updates when needed.

Example triggers include:

* room description changes
* objects added or removed
* builder commands
* scripted world changes

These triggers mark the current image as stale and queue a regeneration job.

You can also cap per-subject history retention by setting `max_image_history` on your typeclass mixin instance/class. When set, only the newest image metadata entries are retained.

---

# Documentation

Full documentation is available in the following files:

| File            | Description                           |
| --------------- | ------------------------------------- |
| USER_MANUAL.md  | Installation and usage guide          |
| ARCHITECTURE.md | System design and generation pipeline |
| BACKEND_API.md  | Backend integration specification     |
| DATA_MODEL.md   | Image metadata and storage model      |

---

# Design Goals

Local-first operation
No cloud dependency required.

Non-blocking gameplay
Image generation always runs asynchronously.

Deterministic reuse
Images can be reused when rooms return to prior states.

Backend flexibility
Different AI pipelines can be integrated.

---

# License

MIT

---
