# evennia-ai-image-generator
Local-first AI image generation for Evennia MUDs

`evennia-ai-image-generator` automatically generates and maintains images for rooms and objects in an Evennia game. When a player uses `look`, the system can:

* Detect whether an image already exists
* Generate one locally using Stable Diffusion-compatible backends
* Preserve visual continuity using prior renders
* Incorporate reference images from contained objects
* Cache the result
* Append a direct image URL to the normal text description

Because telnet cannot render images directly, the system returns hyperlinks to generated image files. Clients such as Discord will automatically embed and preview these URLs.

---

## Goals

* Local-first image generation (no required cloud services)
* Reusable across any Evennia game
* Backend-agnostic (Diffusers, ComfyUI, etc.)
* Async generation (never blocks `look`)
* Visual continuity across revisions
* Reference-aware scene composition

---

## Core Concepts

### 1. Automatic Generation on `look`

When a player looks at a room or object:

* If an image exists → show the link
* If no image exists → queue generation in the background
* Immediately return text with `Image: generating...`

Once generation completes, subsequent `look` commands show the image URL.

---

### 2. Visual Continuity

When a room or object is updated:

* The prior image is passed as a continuity reference
* The backend may use `img2img` refinement instead of full regeneration
* This reduces visual drift and preserves scene identity

---

### 3. Reference-Aware Scene Generation

Room image generation may include:

* Room description
* Notable object descriptions
* Images of contained objects (if available)

This allows room images to reflect important props without hallucinating unrelated content.

---

## Architecture Overview

```
Evennia Object/Room
        ↓
SceneImageMixin
        ↓
Image Context Collection
        ↓
Prompt Builder
        ↓
ImageGenerationRequest
        ↓
Backend (Diffusers / ComfyUI / etc.)
        ↓
Local File Storage
        ↓
Image URL appended to appearance
```

---

## Image Generation Request Model

Backends receive a structured request instead of raw text.

```python
@dataclass
class ReferenceImage:
    path: str
    role: str        # "continuity", "object", "style", "context"
    weight: float = 1.0
    caption: Optional[str] = None

@dataclass
class ImageGenerationRequest:
    subject_type: Literal["room", "object"]
    subject_key: str
    prompt: str
    negative_prompt: str = ""
    mode: Literal["txt2img", "img2img", "refine", "compose"] = "txt2img"
    reference_images: List[ReferenceImage] = field(default_factory=list)
    seed: Optional[int] = None
    width: int = 1024
    height: int = 1024
    strength: Optional[float] = None
    guidance_scale: Optional[float] = None
    style: Optional[str] = None
```

---

## Backend System

Backends implement a common interface:

```python
class BaseImageBackend:
    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": False,
        "inpainting": False,
    }

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        ...
```

### Planned Backends

* `DiffusersBackend` (embedded Stable Diffusion pipeline)
* `ComfyUIBackend` (external local server workflow)

Backends may degrade gracefully depending on supported features.

---

## Data Stored on Rooms and Objects

Each image-capable object maintains metadata:

* `db.image_state` → `none | pending | ready | failed`
* `db.image_url`
* `db.image_path`
* `db.image_prompt`
* `db.image_negative_prompt`
* `db.image_seed`
* `db.image_model`
* `db.image_generated_ts`
* `db.image_revision`
* `db.image_source_refs`
* `db.previous_image_path`

---

## Installation

```
pip install evennia-ai-image-generator
```

Add to your Evennia project:

```python
INSTALLED_APPS += ["evennia_ai_image_generator"]
```

Configure backend in settings:

```python
AI_IMAGE_GENERATOR = {
    "BACKEND": "diffusers",
    "MEDIA_ROOT": "media/scene_images",
    "BASE_URL": "https://your-game.example.com/media/scene_images",
    "DEFAULT_WIDTH": 1024,
    "DEFAULT_HEIGHT": 1024,
}
```

---

## Using the Mixin

To enable image generation for a room:

```python
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia import DefaultRoom

class Room(SceneImageMixin, DefaultRoom):
    pass
```

For objects:

```python
class Object(SceneImageMixin, DefaultObject):
    pass
```

---

## Image Generation Policy

### Rooms

* No image → generate from room text (+ object refs)
* Image exists + room changed → refine from prior image
* Minor changes → optional delayed regeneration

### Objects

* No image → generate from object text
* Image exists + object changed → refine via img2img

---

## Builder Commands

* `imagegen here`
* `imagegen <object>`
* `imageregen <object>`
* `imageclear <object>`
* `imagesetstyle <object> = <style>`
* `imageprompt <object>`

---

## Output Behavior

Appearance text is appended with a direct image link:

```
A dimly lit tavern filled with the smell of smoke and ale.

Image: https://your-game/media/scene_images/rooms/room_76_v2.png
```

Clients such as Discord will embed the image automatically.

---

## Version Roadmap

### v1

* Object txt2img
* Object img2img refinement
* Room txt2img (text + object captions)
* Room img2img refinement
* Async background generation
* Local storage and URL linking

### v2

* Multi-image composition
* Masked inpainting
* Selective regeneration regions
* Style profiles
* Deterministic scene seeds

---

## Why Local-First?

* No external API dependency
* No usage costs
* Full control over model selection
* Works offline
* Privacy-safe for private MUDs

---

## License

MIT

---
