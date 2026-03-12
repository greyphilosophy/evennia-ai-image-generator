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

```
pip install evennia-ai-image-generator
```

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
