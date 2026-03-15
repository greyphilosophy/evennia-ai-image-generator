from evennia_ai_image_generator.backend.placeholder import PlaceholderBackend
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia_ai_image_generator.queue import GenerationQueue, process_generation_job


def test_render_ready_state_includes_image_url() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="tavern", description="A warm tavern")
    room.queue_for_generation()
    process_generation_job(room, PlaceholderBackend())

    output = room.render_look()

    assert room.image_state == "ready"
    assert "Image: https://game.test/media/generated" in output


def test_none_state_queues_and_shows_generating() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="forest", description="A dark forest")
    queued = room.queue_for_generation(reason="look")

    assert queued is True
    assert room.image_state == "pending"
    assert "Image: generating..." in room.render_look()


def test_queue_deduplicates_subject_jobs() -> None:
    queue = GenerationQueue()

    assert queue.queue_image_generation("room-1") is True
    assert queue.queue_image_generation("room-1") is False
    queue.mark_complete("room-1")
    assert queue.queue_image_generation("room-1") is True
