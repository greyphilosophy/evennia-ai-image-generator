from evennia_ai_image_generator.commands import imageclear, imagegen, imageprompt, imageregen
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia_ai_image_generator.queue import GenerationQueue


def test_imagegen_queues_subject_and_marks_pending():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    message = imagegen(subject, queue=queue)

    assert message == "Queued image generation for tavern."
    assert subject.image_state == "pending"
    assert "tavern" in queue.pending


def test_imagegen_returns_pending_message_when_duplicate():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    assert imagegen(subject, queue=queue) == "Queued image generation for tavern."
    assert imagegen(subject, queue=queue) == "Image generation already pending for tavern."


def test_imagegen_duplicate_restores_pending_state_when_subject_is_stale():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    subject.lifecycle.mark_pending(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "old prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )
    subject.mark_image_stale(reason="builder_update")
    queue.queue_image_generation("tavern")

    message = imagegen(subject, queue=queue)

    assert message == "Image generation already pending for tavern."
    assert subject.image_state == "pending"
    assert subject.lifecycle.image_generation["reason"] == "builder_gen"

def test_imagegen_returns_full_message_when_queue_is_at_capacity():
    queue = GenerationQueue(max_pending=1)
    queue.queue_image_generation("already-pending")
    subject = SceneImageMixin(subject_key="tavern")

    message = imagegen(subject, queue=queue)

    assert message == "Image generation queue is full. Please try again shortly."
    assert subject.image_state == "none"
    assert "tavern" not in queue.pending


def test_imagegen_from_ready_state_marks_stale_then_queues():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()
    subject.queue_for_generation(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "old prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )

    message = imagegen(subject, queue=queue)

    assert message == "Queued image generation for tavern."
    assert subject.image_state == "pending"
    assert subject.lifecycle.image_generation["reason"] == "builder_gen"

def test_imageregen_marks_stale_then_pending_and_queues():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()
    subject.queue_for_generation(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "old prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )

    message = imageregen(subject, queue=queue)

    assert message == "Queued image regeneration for tavern."
    assert subject.image_state == "pending"
    assert "tavern" in queue.pending


def test_imageregen_returns_full_message_when_queue_is_at_capacity():
    queue = GenerationQueue(max_pending=1)
    queue.queue_image_generation("already-pending")
    subject = SceneImageMixin(subject_key="tavern")

    message = imageregen(subject, queue=queue)

    assert message == "Image generation queue is full. Please try again shortly."
    assert subject.image_state == "none"
    assert "tavern" not in queue.pending


def test_imageclear_removes_current_image_and_sets_none():
    subject = SceneImageMixin(subject_key="tavern")
    subject.queue_for_generation(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "old prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )

    message = imageclear(subject)

    assert message == "Cleared current image for tavern."
    assert subject.image_state == "none"
    assert subject.image_current is None


def test_imageprompt_prefers_last_prompt_when_available():
    subject = SceneImageMixin(subject_key="tavern", description="Stone floor")
    subject.queue_for_generation(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "stored prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )

    assert imageprompt(subject) == "stored prompt"


def test_imageprompt_builds_new_prompt_when_no_current_image():
    subject = SceneImageMixin(subject_key="tavern", description="Stone floor")

    prompt = imageprompt(subject)

    assert "Stone floor" in prompt


class _Actor:
    def __init__(self, is_builder=False, permissions=None):
        self.is_builder = is_builder
        self.permissions = permissions if permissions is not None else []


def test_imagegen_rejects_non_builder_actor():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    message = imagegen(subject, queue=queue, actor=_Actor())

    assert message == "Only builders can use image management commands."
    assert subject.image_state == "none"
    assert queue.pending_count() == 0


def test_imageregen_accepts_actor_with_builder_permission():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    message = imageregen(subject, queue=queue, actor=_Actor(permissions=["Builder"]))

    assert message == "Queued image regeneration for tavern."
    assert subject.image_state == "pending"


def test_imageclear_rejects_non_builder_actor():
    subject = SceneImageMixin(subject_key="tavern")
    subject.queue_for_generation(reason="look")
    subject.lifecycle.set_ready(
        {
            "image_id": "room_tavern_0001",
            "path": "/tmp/tavern.png",
            "url": "https://example.com/tavern.png",
            "revision": 1,
            "state_fingerprint": "fp1",
            "prompt": "old prompt",
            "model_name": "placeholder",
            "mode": "txt2img",
            "reference_count": 0,
            "reference_fallback_used": False,
            "continuity_fallback_used": False,
        }
    )

    message = imageclear(subject, actor=_Actor())

    assert message == "Only builders can use image management commands."
    assert subject.image_state == "ready"


def test_imageprompt_rejects_non_builder_actor():
    subject = SceneImageMixin(subject_key="tavern", description="Stone floor")

    message = imageprompt(subject, actor=_Actor())

    assert message == "Only builders can use image management commands."


def test_imagegen_accepts_callable_is_builder_flag():
    class _CallableBuilderActor:
        permissions = []

        @staticmethod
        def is_builder() -> bool:
            return True

    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    message = imagegen(subject, queue=queue, actor=_CallableBuilderActor())

    assert message == "Queued image generation for tavern."
    assert subject.image_state == "pending"


def test_imagegen_accepts_string_permissions_container():
    subject = SceneImageMixin(subject_key="tavern")
    queue = GenerationQueue()

    message = imagegen(subject, queue=queue, actor=_Actor(permissions="builder"))

    assert message == "Queued image generation for tavern."
    assert subject.image_state == "pending"
