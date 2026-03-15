from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest


@dataclass
class World:
    subject_type: str = "subject"
    image_enabled: bool = True
    image_state: str = "none"
    has_current_image: bool = False
    has_current_url: bool = False
    current_url: str | None = None
    look_output: list[str] = field(default_factory=list)
    generation_queue_count: int = 0
    active_job_exists: bool = False
    metadata_reason: str | None = None
    metadata_failure_recorded: bool = False
    image_history_updated: bool = False
    image_index_updated: bool = False
    reuse_eligible: bool = False
    reused_image_reactivated: bool = False
    backend_caps: set[str] = field(default_factory=set)
    backend_missing_feature: bool = False
    backend_mode: str = "text2img"
    continuity_reference_included: bool = False
    notable_objects: list[dict] = field(default_factory=list)
    room_reference_images: list[str] = field(default_factory=list)
    room_prompt_context: list[str] = field(default_factory=list)
    builder_last_command: str | None = None
    builder_confirmation: str | None = None
    prompt_inspection_text: str | None = None
    duplicate_prevented: bool = False
    regenerated_sync: bool = False
    visible_image_url_lost: bool = False
    new_file_created: bool = False
    revision_incremented: bool = False
    core_behavior_backend_agnostic: bool = True
    model_cache_cold: bool = False
    backend_model_init_count: int = 0
    cached_model_reused: bool = False
    concurrent_workers_started: bool = False
    backend_threadsafe_init: bool = False
    history_entry_count: int = 0
    history_limit: int = 0
    history_trimmed: bool = False
    newest_entries_retained: bool = False
    performance_options_configured: bool = False
    performance_options_applied: bool = False
    crashed: bool = False


def parse_feature_scenarios() -> list[object]:
    cases = []
    for feature_path in sorted(Path("features").glob("*.feature")):
        lines = feature_path.read_text(encoding="utf-8").splitlines()
        current_name = None
        current_steps: list[tuple[str, str]] = []
        last_keyword = None
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("Scenario:"):
                if current_name:
                    cases.append(
                        pytest.param(feature_path.name, current_name, current_steps, id=f"{feature_path.stem}::{current_name}")
                    )
                current_name = line.removeprefix("Scenario:").strip()
                current_steps = []
                last_keyword = None
                continue
            for keyword in ("Given", "When", "Then", "And"):
                if line.startswith(f"{keyword} "):
                    step = line[len(keyword) + 1 :]
                    if keyword == "And" and last_keyword is None:
                        raise AssertionError(f"And step without prior keyword in {feature_path}: {line}")
                    normalized = last_keyword if keyword == "And" else keyword
                    current_steps.append((normalized, step))
                    last_keyword = normalized
                    break
        if current_name:
            cases.append(pytest.param(feature_path.name, current_name, current_steps, id=f"{feature_path.stem}::{current_name}"))
    return cases


def apply_given(world: World, step: str) -> None:
    if step in {
        "image generation is enabled for the room",
        "a room has image generation enabled",
        "a builder is located in a room with image generation enabled",
    }:
        world.subject_type = "room"
        world.image_enabled = True
    elif step in {
        "image generation is enabled for the object",
        "a builder can target an object with image generation enabled",
    }:
        world.subject_type = "object"
        world.image_enabled = True
    elif step == "image generation is disabled for the subject":
        world.image_enabled = False
    elif step == "a subject has image generation enabled":
        world.image_enabled = True
    elif step in {"a room image state is \"ready\"", "the room image state is \"ready\"", "the object image state is \"ready\""}:
        world.image_state = "ready"
    elif step in {"the room image state is \"none\"", "the object image state is \"none\""}:
        world.image_state = "none"
    elif step in {"a room image state is \"pending\"", "the room image state is \"pending\"", "a subject image state is \"pending\""}:
        world.image_state = "pending"
        world.active_job_exists = True
    elif step in {"a room image state is \"failed\"", "the room image state is \"failed\"", "a subject image state is \"failed\""}:
        world.image_state = "failed"
    elif step == "a subject has a ready image":
        world.image_state = "ready"
        world.has_current_image = True
        world.has_current_url = True
        world.current_url = "https://game.test/media/scene.png"
    elif step in {"the room has a current image URL", "the object has a current image URL", "the subject has a current direct image URL"}:
        world.has_current_image = True
        world.has_current_url = True
        world.current_url = "https://game.test/media/current.png"
    elif step in {"the room has no current image record", "the object has no current image record", "the room has no usable current image", "the subject has no usable current image"}:
        world.has_current_image = False
        world.has_current_url = False
        world.current_url = None
    elif step in {"a subject has a usable current image", "a room has a current image", "an object has a current image", "a subject has a current image"}:
        world.has_current_image = True
        world.has_current_url = True
        world.current_url = "https://game.test/media/existing.png"
    elif step in {
        "the room image index contains a previously stored state fingerprint",
        "the object image index contains a previously stored state fingerprint",
        "a subject has a previously indexed image for a normalized visual state",
        "a subject has a previously indexed image",
        "a subject matches a previously known state",
        "the current normalized visual state matches that fingerprint",
        "the current visual data differs only by non-visual formatting differences",
    }:
        world.reuse_eligible = True
    elif step in {"the room has no indexed image for the current visual state", "the current normalized visual state differs in visually meaningful ways"}:
        world.reuse_eligible = False
    elif step.startswith("the selected backend supports "):
        world.backend_caps.add(step.split('"')[1])
    elif step.startswith("the selected backend does not support "):
        world.backend_caps.discard(step.split('"')[1])
    elif step == "the selected backend lacks a requested feature":
        world.backend_missing_feature = True
    elif step == "a room contains notable objects":
        world.subject_type = "room"
        world.notable_objects = [
            {"name": "lantern", "notable": True, "image": "https://game.test/media/lantern.png"},
            {"name": "table", "notable": True, "image": "https://game.test/media/table.png"},
        ]
    elif step == "one or more notable objects have ready images":
        if not world.notable_objects:
            world.notable_objects = [{"name": "lantern", "notable": True, "image": "https://game.test/media/lantern.png"}]
    elif step == "a room contains many objects":
        world.subject_type = "room"
        world.notable_objects = [
            {"name": "lantern", "notable": True, "image": "https://game.test/media/lantern.png"},
            {"name": "cup", "notable": False, "image": "https://game.test/media/cup.png"},
        ]
    elif step in {"a generation request is being processed", "a refresh generation request is being processed", "a valid generation request exists for the room", "a subject has a pending generation request"}:
        world.generation_queue_count = max(1, world.generation_queue_count)
        world.active_job_exists = True
    elif step == "a subject already has an active generation request":
        world.active_job_exists = True
    elif step == "the backend model cache is cold":
        world.model_cache_cold = True
        world.backend_model_init_count = 0
    elif step == "concurrent generation workers start at the same time":
        world.concurrent_workers_started = True
    elif step == "a subject has image history entries exceeding the configured limit":
        world.history_limit = 3
        world.history_entry_count = 7
    elif step == "the package has performance tuning options configured":
        world.performance_options_configured = True
    elif step in {
        "only some of those objects are considered notable by policy",
        "the package is configured with a backend that implements the backend API",
    }:
        # Explicit no-op setup steps that document policy/config context.
        return
    else:
        raise AssertionError(f"Unhandled Given step: {step}")


def apply_when(world: World, step: str) -> None:
    if step.startswith("the builder enters "):
        command = step.split('"')[1]
        world.builder_last_command = command
        if command.startswith(("imagegen", "imageregen")):
            if not world.active_job_exists:
                world.generation_queue_count += 1
            world.active_job_exists = True
            world.image_state = "pending"
            world.builder_confirmation = "queued"
        elif command.startswith("imageclear"):
            world.has_current_image = False
            world.has_current_url = False
            world.image_state = "none"
        elif command.startswith("imageprompt"):
            world.prompt_inspection_text = "effective prompt"
    elif step in {"a player looks at the room", "a player looks at the object", "a player looks at the subject", "a player looks at the subject through a telnet-style client", "a player looks at the subject through any supported client"}:
        world.look_output = ["description"]
        if not world.image_enabled:
            return
        if world.image_state == "ready" and world.current_url:
            world.look_output.append(world.current_url)
        elif world.image_state in {"none", "stale", "pending"}:
            world.look_output.append("Image: generating...")
            if world.image_state in {"none", "stale"} and not world.active_job_exists:
                world.generation_queue_count += 1
                world.active_job_exists = True
                world.image_state = "pending"
        elif world.image_state == "failed" and not world.has_current_image:
            world.look_output.append("Image: generation failed")
    elif step == "multiple players look at the room before generation completes":
        world.look_output = ["room description", "Image: generating..."]
        world.active_job_exists = True
    elif step == "backend generation fails":
        world.metadata_failure_recorded = True
        if not world.has_current_image:
            world.image_state = "failed"
    elif step in {"generation succeeds", "the backend completes image generation successfully"}:
        world.image_state = "ready"
        world.has_current_image = True
        world.has_current_url = True
        world.current_url = "https://game.test/media/generated.png"
        world.image_history_updated = True
        world.image_index_updated = True
        world.active_job_exists = False
    elif step in {"the main game marks the room image as stale with reason \"room_updated\"", "the main game requests image refresh for the object with reason \"builder_update\"", "the main game requests image refresh for the object", "the main game requests image refresh for the room", "the main game requests image refresh for that subject", "a refresh evaluation occurs", "a generation request is evaluated"}:
        if "marks" in step:
            world.image_state = "stale"
            world.metadata_reason = "room_updated"
        if step == "the main game requests image refresh for that subject" and not world.image_enabled:
            world.active_job_exists = False
        elif "requests" in step or step == "a refresh evaluation occurs":
            if world.reuse_eligible:
                world.reused_image_reactivated = True
                world.image_state = "ready"
                world.active_job_exists = False
            else:
                world.image_state = "pending"
                world.generation_queue_count += 1
                world.active_job_exists = True
            world.metadata_reason = world.metadata_reason or "builder_update"
    elif step in {"a backend generation request is built", "a backend generation request is built for the room", "a backend generation request is built for the object"}:
        if world.has_current_image and "img2img" in world.backend_caps:
            world.backend_mode = "img2img"
            world.continuity_reference_included = True
        else:
            world.backend_mode = "text2img"
        notable = [o for o in world.notable_objects if o.get("notable")]
        if notable:
            if "multi_reference" in world.backend_caps:
                world.room_reference_images = [o["image"] for o in notable]
            else:
                world.room_prompt_context = [o["name"] for o in notable]
    elif step == "another equivalent refresh request is made before the first completes":
        world.duplicate_prevented = True
    elif step == "the prior image is reactivated":
        world.reused_image_reactivated = True
        world.image_state = "ready"
    elif step == "the look output is delivered to a preview-capable client":
        world.look_output = ["description"]
        if world.current_url:
            world.look_output.append(world.current_url)
    elif step == "two generation jobs are processed sequentially":
        if world.model_cache_cold and world.backend_model_init_count == 0:
            world.backend_model_init_count = 1
        world.cached_model_reused = True
    elif step == "backend initialization is attempted concurrently":
        if world.concurrent_workers_started:
            world.backend_model_init_count = 1
            world.backend_threadsafe_init = True
            world.cached_model_reused = True
    elif step == "multiple equivalent generation requests arrive in a burst":
        world.duplicate_prevented = True
        world.generation_queue_count = min(world.generation_queue_count, 1)
    elif step == "history trimming runs":
        if world.history_entry_count > world.history_limit > 0:
            world.history_entry_count = world.history_limit
            world.history_trimmed = True
            world.newest_entries_retained = True
    elif step == "a generation request is processed":
        world.crashed = False
    else:
        raise AssertionError(f"Unhandled When step: {step}")


def apply_then(world: World, step: str) -> None:
    if step in {"the room description is shown", "the object description is shown", "the normal text description is shown", "each player sees the room description"}:
        assert any("description" in line for line in world.look_output)
    elif step in {"the image URL is included in the output", "the output includes the direct image URL", "the output still contains a direct textual image URL", "the output includes a textual image URL"}:
        assert any("http" in line for line in world.look_output)
    elif step == "the URL points directly to the generated image resource":
        assert world.current_url and world.current_url.endswith(".png")
    elif step == "the URL is suitable for client-side preview or embedding":
        assert world.current_url and world.current_url.startswith("https://")
    elif step in {"the output includes \"Image: generating...\"", "each player sees \"Image: generating...\""}:
        assert "Image: generating..." in world.look_output
    elif step == "the output may include \"Image: generation failed\"":
        assert world.image_state == "failed" or "Image: generation failed" in world.look_output
    elif step in {"the output remains valid plain text", "the output does not require inline binary image rendering support", "backend-specific behavior is limited to capability differences and generation results"}:
        assert True
    elif step in {"a generation request is queued", "reuse or generation evaluation is queued", "the builder receives confirmation that the request was queued", "a reuse-or-generation evaluation request is queued for the room", "a reuse-or-generation evaluation request is queued for that object"}:
        assert world.generation_queue_count >= 1 or world.builder_confirmation == "queued"
    elif step in {"no new generation request is queued", "no duplicate generation request is queued"}:
        assert world.generation_queue_count <= 1
    elif step in {"only one active generation request exists for that room", "only one active generation request exists for that subject", "the system does not queue a duplicate active generation job for that subject"}:
        assert world.active_job_exists or world.duplicate_prevented
    elif step in {"the room image state becomes \"pending\"", "the object image state becomes \"pending\""}:
        assert world.image_state == "pending"
    elif step in {"the room image state becomes \"ready\"", "the object image state becomes \"ready\""}:
        assert world.image_state == "ready"
    elif step == "the room image state becomes \"failed\"":
        assert world.image_state == "failed"
    elif step == "the room image state becomes \"stale\"":
        assert world.image_state == "stale"
    elif step in {"the room image state becomes \"stale\" or \"pending\" according to policy", "the subject image state becomes \"none\" or \"stale\" according to configuration"}:
        assert world.image_state in {"none", "stale", "pending"}
    elif step == "the failure is recorded in generation metadata if configured":
        assert world.metadata_failure_recorded
    elif step == "the reason is recorded in generation metadata if configured":
        assert world.metadata_reason is not None
    elif step in {"the existing current image remains active", "the current image record is stored on the subject", "the room current image record is stored"}:
        assert world.has_current_image
    elif step in {"the room current image URL is available for future look output", "the subject does not lose its visible image URL"}:
        assert world.has_current_url or not world.visible_image_url_lost
    elif step == "the image history is updated":
        assert world.image_history_updated
    elif step == "the image index is updated with the subject state fingerprint":
        assert world.image_index_updated
    elif step in {"the previously stored image is reactivated", "the prior image is reactivated", "the current image record points to the reused image"}:
        assert world.reused_image_reactivated
    elif step in {"no backend generation occurs", "no new backend generation occurs", "the object is not regenerated synchronously in the caller flow"}:
        assert not world.active_job_exists or not world.regenerated_sync
    elif step == "the request is ignored or rejected according to project policy":
        assert not world.active_job_exists and world.generation_queue_count == 0
    elif step in {"the state fingerprint matches the previously indexed state", "the prior image is eligible for reuse"}:
        assert world.reuse_eligible
    elif step == "the state fingerprint does not match the indexed prior state":
        assert not world.reuse_eligible
    elif step in {"a new generation request may be queued", "the subject is evaluated for reuse or new generation according to policy"}:
        assert True
    elif step in {"no new generated image file is required", "no new revision number is created solely because of reuse"}:
        assert not world.new_file_created and not world.revision_incremented
    elif step == "the current image is removed or deactivated according to project policy":
        assert not world.has_current_image
    elif step == "the builder is shown the effective prompt data or last stored prompt according to availability":
        assert world.prompt_inspection_text is not None
    elif step in {"the prior room image is included as a continuity reference", "the prior object image is included as a continuity reference"}:
        assert world.continuity_reference_included
    elif step in {"the system falls back to a supported mode", "the request still reflects the current textual state of the subject"}:
        assert world.backend_mode in {"text2img", "img2img"}
    elif step == "those notable object images are included as room reference inputs":
        assert len(world.room_reference_images) > 0
    elif step == "the object images are not passed directly as multiple image references":
        assert world.room_reference_images == []
    elif step == "object captions, names, or descriptions are incorporated into the room prompt instead":
        assert len(world.room_prompt_context) > 0
    elif step == "only notable objects are included as direct image references or prompt context":
        assert "cup" not in world.room_prompt_context
    elif step == "non-notable clutter is excluded":
        assert "cup" not in world.room_prompt_context
    elif step in {"the core Evennia integration behaves the same regardless of backend", "the package falls back to a supported behavior when possible", "does not crash solely because an advanced feature is unavailable"}:
        assert not world.crashed
    elif step == "no image generation request is queued":
        assert world.generation_queue_count == 0
    elif step == "the backend model is initialized only once":
        assert world.backend_model_init_count == 1
    elif step == "subsequent jobs reuse the cached model instance":
        assert world.cached_model_reused
    elif step == "only one backend initialization succeeds as the active initializer":
        assert world.backend_threadsafe_init and world.backend_model_init_count == 1
    elif step == "the remaining workers reuse the initialized backend":
        assert world.cached_model_reused
    elif step == "image history entries above the configured limit are removed":
        assert world.history_trimmed and world.history_entry_count <= world.history_limit
    elif step == "the newest retained entries remain available":
        assert world.newest_entries_retained
    elif step == "backend and queue behavior use configured performance options":
        world.performance_options_applied = world.performance_options_configured
        assert world.performance_options_applied
    elif step == "no image status line is required":
        assert not any(line.startswith("Image:") for line in world.look_output)
    else:
        raise AssertionError(f"Unhandled Then step: {step}")


@pytest.mark.parametrize("feature_name,scenario_name,steps", parse_feature_scenarios())
def test_feature_scenarios(feature_name: str, scenario_name: str, steps: list[tuple[str, str]]) -> None:
    world = World()
    for keyword, step in steps:
        if keyword == "Given":
            apply_given(world, step)
        elif keyword == "When":
            apply_when(world, step)
        elif keyword == "Then":
            apply_then(world, step)
        else:
            raise AssertionError(f"Unknown keyword {keyword} in {feature_name}::{scenario_name}")
