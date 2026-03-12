---

# evennia-ai-image-generator

## User Manual

---

# 1. Introduction

`evennia-ai-image-generator` adds AI-generated images to rooms and objects in an Evennia MUD.

When a player examines something with `look`, the system can automatically generate an image if one does not already exist.

Because traditional MUD clients cannot display images directly, the system returns a hyperlink to the generated image.

Clients like **Discord** will automatically embed the image preview.

Example output:

```
A dimly lit tavern filled with the smell of smoke and spilled ale.

Image: https://yourgame.com/media/scene_images/rooms/tavern_001.png
```

The first time the room is viewed the image will be generated in the background.

---

# 2. Key Features

Automatic generation
Images are created the first time a room or object is viewed.

Local AI generation
Images are generated locally using Stable Diffusion compatible backends.

Visual continuity
When rooms or objects change, previous images are used as references to maintain visual consistency.

Reference-aware scenes
Room images can incorporate images of notable objects in the room.

Async operation
Image generation never blocks gameplay.

Reusable system
Any Evennia game can install and use this package.

---

# 3. Requirements

To run the image generator you need:

Evennia server
Python 3.10+

One supported AI backend:

Option A — Diffusers (recommended for local installs)
Option B — ComfyUI (recommended for advanced workflows)

GPU acceleration is recommended but not required.

---

# 4. Installation

Install the package:

```
pip install evennia-ai-image-generator
```

Add the module to your Evennia project settings:

```
INSTALLED_APPS += ["evennia_ai_image_generator"]
```

Run migrations if needed:

```
evennia migrate
```

---

# 5. Basic Configuration

Add the image generator settings to your Evennia settings file.

Example:

```
AI_IMAGE_GENERATOR = {

    BACKEND: "diffusers",

    MEDIA_ROOT: "media/scene_images",

    BASE_URL: "https://yourgame.com/media/scene_images",

    DEFAULT_WIDTH: 1024,

    DEFAULT_HEIGHT: 1024,

    GENERATION_MODE: "balanced"
}
```

Generation mode controls visual continuity.

loose
Images regenerate freely.

balanced
Prior images are used as references when possible.

strict
Strong preference for refining prior images.

---

# 6. Enabling Image Generation

Image generation is enabled by adding the mixin to your room and object typeclasses.

Example room:

```
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia import DefaultRoom

class Room(SceneImageMixin, DefaultRoom):
    pass
```

Example object:

```
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia import DefaultObject

class Object(SceneImageMixin, DefaultObject):
    pass
```

Once the mixin is added, image generation will automatically integrate with the `look` command.

---

# 7. How Image Generation Works

When a player uses `look`:

1. The system checks whether the object has an image.

2. If an image exists
   the link is displayed.

3. If no image exists
   the system queues a background job to generate one.

4. The player sees:

```
Image: generating...
```

5. Once generation finishes future `look` commands show the image URL.

---

# 8. Visual Continuity

When rooms or objects are updated the system attempts to preserve visual identity.

If a previous image exists it will be used as a reference.

Example workflow:

```
Room created → txt2img generation
Room modified → img2img refinement
```

This reduces visual drift and keeps locations recognizable.

---

# 9. Reference Images

Room images may incorporate objects present in the room.

For example:

```
Room: Wizard Laboratory

Objects:
    Crystal Orb
    Spellbook
    Alchemy Table
```

If those objects already have images, they may be used as references when generating the room image.

This improves scene coherence.

Only **notable objects** are included to avoid overcrowding the scene.

---

# 10. Image Storage

Generated images are stored locally.

Example structure:

```
media/
  scene_images/
      rooms/
      objects/
```

Each image is versioned to allow continuity.

Example:

```
tavern_v1.png
tavern_v2.png
```

---

# 11. Builder Commands

Builders can control image generation manually.

Generate image for current room:

```
imagegen here
```

Generate image for an object:

```
imagegen <object>
```

Regenerate an image:

```
imageregen <object>
```

Remove image:

```
imageclear <object>
```

View the prompt used to generate an image:

```
imageprompt <object>
```

---

# 12. Customizing Prompts

Games may customize the visual prompt template.

Example prompt template:

```
A fantasy illustration of {room_name}

Scene description:
{room_desc}

Notable objects:
{object_list}

Atmosphere:
dramatic lighting, detailed environment art
```

Prompts can be overridden in configuration.

---

# 13. Performance Tips

Image generation can be computationally expensive.

Recommended practices:

Generate images lazily
Only generate images when first viewed.

Limit reference objects
Use a maximum of 3–6 objects in scene generation.

Use GPU acceleration
Stable Diffusion performs best on GPU.

Use async workers
Generation runs in background threads.

---

# 14. Troubleshooting

Images never appear

Check the media directory exists and is writable.

Images generate but links fail

Verify BASE_URL points to a public static file path.

Generation is slow

Reduce resolution or use GPU acceleration.

Objects do not appear in room images

Ensure they are marked as notable or have existing images.

---

# 15. Advanced Usage

Developers can extend the system with custom backends.

Example backend types:

Stable Diffusion via Diffusers
ComfyUI workflows
Remote inference servers
Custom diffusion pipelines

Backends only need to implement the `BaseImageBackend` interface.

---

# 16. Future Features

Planned improvements include:

Multi-image composition
Selective inpainting
Style packs
Scene seed consistency
Region-based updates

---
