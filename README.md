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

## Quick install (recommended)

```bash
# Clone the repo
git clone https://github.com/greyphilosophy/evennia-ai-image-generator.git
cd evennia-ai-image-generator

# Install core dependencies
pip install -r requirements.txt
```

## Install via pip from GitHub

```bash
# Core dependencies (ComfyUI backend)
pip install git+https://github.com/greyphilosophy/evennia-ai-image-generator.git

# With Diffusers backend (requires GPU + CUDA)
pip install "git+https://github.com/greyphilosophy/evennia-ai-image-generator.git#egg=evennia-ai-image-generator[diffusers]"

# With test dependencies
pip install "git+https://github.com/greyphilosophy/evennia-ai-image-generator.git#egg=evennia-ai-image-generator[test]"
```

## Set up your Evennia game

After installing, add to your Evennia `settings.py`:

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

Run migrations:

```bash
evennia migrate
```

### Optional: Configure the backend

For **ComfyUI** backend (recommended — no GPU needed if running externally):

```python
IMAGE_BACKEND = {
    "backend": "comfyui",
    "options": {
        "server_url": "http://127.0.0.1:8188",
        "default_steps": 20,
        "default_cfg": 7.5,
    },
}
```

For **Diffusers** backend (needs local GPU + CUDA):

```python
IMAGE_BACKEND = {
    "backend": "diffusers",
    "options": {
        "model_id": "runwayml/stable-diffusion-v1-5",
        "device": "cuda",
    },
}
```

### Legacy: PYTHONPATH or vendor approaches

If you prefer not to use pip, cloning with PYTHONPATH or vendoring still works — see `docs/legacy-install.md`.

### Troubleshooting: `evennia migrate` cannot import settings

If you get an import error, check these in order:

1. **Run from the game directory** (the one containing `server/conf/settings.py`):

```bash
cd ~/muddev/aicompany_mud
evennia migrate
```

2. **Do not replace `INSTALLED_APPS`**. Append instead:

```python
# correct
INSTALLED_APPS += ["evennia_ai_image_generator"]

# incorrect (overwrites Evennia defaults)
# INSTALLED_APPS = ["evennia_ai_image_generator"]
```

3. **Confirm Python can import the package in the same shell**:

```bash
python -c "import evennia_ai_image_generator; print('ok')"
```

4. **Verify your `PYTHONPATH` correctly** (in Bash/Zsh, use `echo`, not `PYTHONPATH` as a command):

```bash
echo "$PYTHONPATH"
```

If you see the repo path more than once, or a trailing `:`, that's usually harmless.
To deduplicate it in your current shell:

```bash
export PYTHONPATH="$HOME/muddev/evennia-ai-image-generator"
```

5. **Validate your Evennia settings file syntax/import directly**:

```bash
python -m py_compile server/conf/settings.py
python -c "import server.conf.settings; print('settings import ok')"
```

6. **Try both migrate commands** (Evennia can sometimes emit a generic config error in one mode):

```bash
evennia migrate --traceback
evennia migrate
```

If plain `evennia migrate` succeeds, your setup is likely fine.

7. **Isolate whether the failure is from `evennia_ai_image_generator` or existing settings**:

- Temporarily comment out the `INSTALLED_APPS += ["evennia_ai_image_generator"]` line.
- Run `evennia migrate` again.
- If it still fails, the root cause is in your base settings/environment, not this package.

8. **If migrate succeeds but warns about model changes not yet reflected in migrations**, that warning comes from your game apps and is separate from this package.

9. **If using Option A, ensure `PYTHONPATH` is exported in the same terminal session**
   before running Evennia commands.

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

### ComfyUI backend setup

The ComfyUI backend talks to a running [ComfyUI](https://github.com/comfyanonymous/ComfyUI) server via its REST API — no HuggingFace pipeline dependencies required.

**Prerequisites:**

1. **Install ComfyUI** and download at least one checkpoint (e.g. Stable Diffusion 1.5):

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
# Download a checkpoint to models/checkpoints/
# e.g. Stable Diffusion 1.5, SDXL, Flux, etc.
```

2. **Start the server** (default port 8188):

```bash
cd ComfyUI && python main.py --listen 127.0.0.1 --port 8188
```

3. **Configure the backend** in your Evennia settings:

```python
IMAGE_BACKEND = {
    "backend": "comfyui",
    "options": {
        "server_url": "http://127.0.0.1:8188",
        "checkpoint": "v1-5-pruned-emaonly.safetensors",  # optional; picks first if omitted
        "scheduler": "karras",
        "sampler_name": "euler",
        "default_steps": 20,
        "default_cfg": 7.5,
        "output_dir": "generated",
        "media_url_base": "http://localhost:4001/media/generated",
    },
}
```

**Configuration options:**

| Option | Default | Description |
|--------|---------|-------------|
| `server_url` | `http://127.0.0.1:8188` | ComfyUI API endpoint |
| `checkpoint` | *(first available)* | Exact checkpoint filename to use |
| `scheduler` | `karras` | Sampler scheduler (karras, simple, sgm_uniform, etc.) |
| `sampler_name` | `euler` | Sampler name (euler, dpmpp_2m, etc.) |
| `default_steps` | 20 | Inference steps per generation |
| `default_cfg` | 7.5 | Guidance scale |
| `output_dir` | `generated` | Local output directory |
| `media_url_base` | `https://game.test/media/generated` | Base URL for serving images |
| `timeout_s` | 120 | HTTP timeout per request (seconds) |
| `max_wait_s` | 600 | Max wait for a single generation (seconds) |
| `dry_run` | False | Return deterministic result without calling ComfyUI |

You can also resolve runtime services from one config dictionary:

```python
from evennia_ai_image_generator import build_runtime_services

services = build_runtime_services({
    "backend": {
        "backend": "comfyui",
        "options": {
            "server_url": "http://127.0.0.1:8188",
            "default_steps": 20,
            "default_cfg": 7.5,
        },
    },
    "queue": {"max_pending": 10},
    "max_image_history": 25,
})
```

**Advantages of ComfyUI backend:**

- ✅ No diffusers/torch dependency required — pure REST API
- ✅ Works with any ComfyUI checkpoint (SD 1.5, SDXL, Flux, etc.)
- ✅ Leverages existing ComfyUI custom nodes for advanced workflows
- ✅ Model stays loaded in ComfyUI — fast subsequent generations
- ✅ GPU acceleration if ComfyUI is running with CUDA

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
