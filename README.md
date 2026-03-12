# README.md

## evennia-ai-image-generator

AI-generated images for rooms and objects in Evennia MUDs.

`evennia-ai-image-generator` automatically creates and maintains images for rooms and objects when players view them. Images are generated locally using Stable Diffusion–compatible pipelines and returned as URLs that can be embedded by modern clients such as Discord.

The system is designed to be lightweight, asynchronous, and reusable across any Evennia game.

---

## Features

* Automatic image generation on `look`
* Local AI pipelines (no cloud dependency)
* Visual continuity using prior renders
* Optional reference images from objects in the room
* Backend-agnostic design
* Non-blocking async generation
* Builder commands for manual control

---

## Example Output

```
A dimly lit tavern filled with the smell of smoke and spilled ale.

Image: https://yourgame.com/media/scene_images/rooms/tavern_v1.png
```

When viewed in Discord, the image preview is automatically embedded.

---

## Installation

```
pip install evennia-ai-image-generator
```

Add to your Evennia project:

```python
INSTALLED_APPS += ["evennia_ai_image_generator"]
```

Enable the mixin in your typeclasses:

```python
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia import DefaultRoom

class Room(SceneImageMixin, DefaultRoom):
    pass
```

---

## Documentation

See the following documents for more details:

| File            | Description                             |
| --------------- | --------------------------------------- |
| USER_MANUAL.md  | Installation and usage guide            |
| ARCHITECTURE.md | System design and generation pipeline   |
| BACKEND_API.md  | How image generation backends integrate |

---

## Supported Backends

Planned backends include:

* Diffusers (embedded Stable Diffusion)
* ComfyUI (external workflow server)

Additional backends can be added by implementing the `BaseImageBackend` interface.

---

## Design Goals

* Local-first generation
* Async operation
* Visual continuity
* Reusable across Evennia games
* Backend-agnostic architecture

---

## License

MIT

---
