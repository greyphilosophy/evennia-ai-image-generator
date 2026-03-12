# BACKEND_API.md

Backend API Specification for **evennia-ai-image-generator**

---

# 1. Purpose

The backend API defines how image generation engines integrate with `evennia-ai-image-generator`.

Backends translate a structured **ImageGenerationRequest** into model-specific operations such as Stable Diffusion pipelines or external workflow engines.

The Evennia integration layer must remain independent of specific AI frameworks.
This allows different engines to be used without modifying the core system.

Examples of supported engines include:

* Stable Diffusion via **Diffusers**
* **ComfyUI** workflow servers
* Custom inference servers
* Future diffusion or rendering pipelines

---

# 2. Backend Responsibilities

A backend is responsible for:

* accepting a structured generation request
* converting it into model-specific instructions
* executing the generation pipeline
* saving the resulting image
* returning metadata about the generated image

Backends must **not** depend on Evennia objects directly.

All inputs are provided through the request structure.

---

# 3. Backend Interface

Every backend must implement the `BaseImageBackend` interface.

Example:

```python
class BaseImageBackend:

    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": False,
        "inpainting": False,
    }

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """
        Generate an image using the provided request.

        Parameters
        ----------
        request : ImageGenerationRequest
            Structured description of the generation task.

        Returns
        -------
        ImageGenerationResult
        """
        raise NotImplementedError
```

---

# 4. ImageGenerationRequest

The request object describes the generation task.

Backends should not assume the request originates from Evennia.

Example structure:

```python
@dataclass
class ReferenceImage:

    path: str
    role: str
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

# 5. ImageGenerationResult

Backends return a result object describing the generated image.

Example:

```python
@dataclass
class ImageGenerationResult:

    image_path: str

    seed: Optional[int]

    model_name: str

    generation_time: float

    metadata: dict = field(default_factory=dict)
```

The Evennia layer uses this information to update object metadata.

---

# 6. Capability Negotiation

Backends advertise supported features through the `capabilities` dictionary.

Example:

```
{
    "txt2img": True,
    "img2img": True,
    "multi_reference": False,
    "inpainting": False
}
```

The core system may adjust generation behavior based on these capabilities.

Examples:

If `img2img` is unsupported:

```
fallback → txt2img
```

If `multi_reference` is unsupported:

```
convert object images → textual context
```

---

# 7. Reference Image Roles

Reference images provide visual context for generation.

Each reference image includes a **role** describing its purpose.

Supported roles include:

### continuity

The previous image of the same object or room.

Used to preserve visual identity.

### object

Image of an object contained in a room.

Used to anchor the object in the scene.

### style

Reference image describing desired artistic style.

### context

Optional environmental references.

Example:

```
ReferenceImage(
    path="images/orb.png",
    role="object",
    caption="glowing crystal orb"
)
```

---

# 8. Generation Modes

The system defines several generation modes.

Backends may implement some or all of them.

---

### txt2img

Create a new image from text.

Inputs:

* prompt
* optional reference images

Used when no previous image exists.

---

### img2img

Refine an existing image.

Inputs:

* previous image
* updated prompt

Used when updating rooms or objects.

---

### refine

A specialized img2img workflow emphasizing continuity.

---

### compose

Future mode combining multiple reference images into a scene.

---

# 9. File Handling

Backends must write generated images to disk.

The request does not include the output path.

Instead the Evennia layer provides the backend with a preallocated path.

Example workflow:

```
Evennia layer chooses output path
        ↓
backend writes image
        ↓
backend returns path in result
```

Backends must not modify paths outside the designated directory.

---

# 10. Deterministic Generation

Backends should support deterministic generation when possible.

If a seed is provided in the request:

```
use provided seed
```

If no seed is provided:

```
generate seed
return seed in result
```

This allows future regeneration of the same image.

---

# 11. Error Handling

Backends must raise exceptions when generation fails.

Examples:

```
ImageGenerationError
BackendConfigurationError
ModelLoadError
```

The Evennia layer will catch errors and mark image generation as failed.

Objects with failed generation will show:

```
Image: generation failed
```

---

# 12. Performance Considerations

Backends should:

* reuse loaded models
* avoid reinitializing pipelines
* minimize disk I/O
* respect configured resolution limits

---

# 13. Backend Discovery

Backends are registered through configuration.

Example:

```
AI_IMAGE_GENERATOR = {

    BACKEND: "diffusers"
}
```

The system loads the corresponding backend class dynamically.

Example mapping:

```
diffusers → DiffusersBackend
comfyui → ComfyUIBackend
```

---

# 14. Example Backend

Minimal backend example:

```python
class ExampleBackend(BaseImageBackend):

    capabilities = {
        "txt2img": True,
        "img2img": False,
    }

    def generate(self, request):

        image = fake_image_generator(request.prompt)

        path = save_image(image)

        return ImageGenerationResult(
            image_path=path,
            seed=request.seed,
            model_name="example"
        )
```

---

# 15. Future Extensions

Possible future backend capabilities include:

* multi-reference composition
* masked inpainting
* depth-aware generation
* controlnet support
* object placement hints

The API is designed to support these without breaking compatibility.

---
