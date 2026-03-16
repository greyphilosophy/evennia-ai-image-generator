from evennia_ai_image_generator.backend.base import ImageGenerationResult
from evennia_ai_image_generator.backend.placeholder import PlaceholderBackend
from evennia_ai_image_generator.mixins import SceneImageMixin
from evennia_ai_image_generator.queue import GenerationQueue, build_generation_queue, process_generation_job


class TxtOnlyBackend(PlaceholderBackend):
    capabilities = {
        "txt2img": True,
        "img2img": False,
        "multi_reference": False,
        "inpainting": False,
    }

    def __init__(self) -> None:
        super().__init__()
        self.last_mode = None

    def generate(self, request):
        self.last_mode = request.mode
        return super().generate(request)


class Img2ImgBackend(PlaceholderBackend):
    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": False,
        "inpainting": False,
    }

    def __init__(self) -> None:
        super().__init__()
        self.last_mode = None

    def generate(self, request):
        self.last_mode = request.mode
        return super().generate(request)


class RequestCapturingBackend(PlaceholderBackend):
    capabilities = {
        "txt2img": True,
        "img2img": True,
        "multi_reference": True,
        "inpainting": False,
    }

    def __init__(self) -> None:
        super().__init__()
        self.last_request = None

    def generate(self, request):
        self.last_request = request
        return ImageGenerationResult(
            image_path="generated/captured.png",
            image_url="https://game.test/media/generated/captured.png",
            seed=None,
            model_name="capture-v1",
            generation_time=0.01,
        )


class ReferencedSubject(SceneImageMixin):
    def collect_reference_images(self):
        return [
            {"path": "generated/lantern.png", "role": "object", "caption": "brass lantern"},
            {"path": "generated/orb.png", "role": "object", "caption": "glowing orb"},
        ]


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


def test_queue_can_enforce_max_pending_capacity() -> None:
    queue = GenerationQueue(max_pending=2)

    assert queue.queue_image_generation("room-1") is True
    assert queue.queue_image_generation("room-2") is True
    assert queue.queue_image_generation("room-3") is False

    queue.mark_complete("room-2")
    assert queue.queue_image_generation("room-3") is True


def test_enqueue_with_status_reports_duplicate_and_full_states() -> None:
    queue = GenerationQueue(max_pending=1)

    assert queue.enqueue_with_status("room-1") == "queued"
    assert queue.enqueue_with_status("room-1") == "duplicate"
    assert queue.enqueue_with_status("room-2") == "full"


def test_queue_introspection_helpers_reflect_state() -> None:
    queue = GenerationQueue()

    assert queue.pending_count() == 0
    assert queue.is_queued("room-1") is False

    queue.queue_image_generation("room-1")
    assert queue.pending_count() == 1
    assert queue.is_queued("room-1") is True

    queue.mark_complete("room-1")
    assert queue.pending_count() == 0
    assert queue.is_queued("room-1") is False




def test_queue_rejects_boolean_max_pending_value() -> None:
    for invalid in (True, False):
        try:
            GenerationQueue(max_pending=invalid)
        except ValueError as err:
            assert "boolean" in str(err)
        else:
            raise AssertionError("Expected ValueError for boolean max_pending")
def test_queue_rejects_invalid_max_pending_value() -> None:
    try:
        GenerationQueue(max_pending=0)
    except ValueError as err:
        assert "max_pending" in str(err)
    else:
        raise AssertionError("Expected ValueError for invalid max_pending")




def test_queue_deduplicates_under_concurrency() -> None:
    from concurrent.futures import ThreadPoolExecutor

    queue = GenerationQueue()

    def attempt() -> bool:
        return queue.queue_image_generation("room-threads")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: attempt(), range(32)))

    assert sum(results) == 1

def test_process_generation_job_falls_back_to_txt2img_when_img2img_unsupported() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="forest", description="A dark forest")
    room.queue_for_generation(reason="look")
    process_generation_job(room, PlaceholderBackend())
    room.mark_image_stale(reason="updated")
    room.queue_for_generation(reason="look")

    backend = TxtOnlyBackend()
    image = process_generation_job(room, backend=backend)

    assert backend.last_mode == "txt2img"
    assert image["mode"] == "txt2img"


def test_process_generation_job_uses_img2img_when_supported() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="forest", description="A dark forest")
    room.queue_for_generation(reason="look")
    process_generation_job(room, PlaceholderBackend())
    room.mark_image_stale(reason="updated")
    room.queue_for_generation(reason="look")

    backend = Img2ImgBackend()
    image = process_generation_job(room, backend=backend)

    assert backend.last_mode == "img2img"
    assert image["mode"] == "img2img"


def test_process_generation_job_loads_backend_from_config() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="square", description="A busy square")
    room.queue_for_generation(reason="look")

    image = process_generation_job(room, backend_config={"backend": "placeholder"})

    assert image["model_name"] == "placeholder-v1"


def test_reference_images_are_passed_when_backend_supports_multi_reference() -> None:
    room = ReferencedSubject(subject_type="room", subject_key="gallery", description="A curated gallery")
    room.queue_for_generation(reason="look")
    backend = RequestCapturingBackend()

    image = process_generation_job(room, backend=backend)

    assert backend.last_request is not None
    assert len(backend.last_request.reference_images) == 2
    assert image["reference_count"] == 2
    assert image["reference_fallback_used"] is False


def test_reference_images_fallback_to_prompt_when_backend_lacks_multi_reference() -> None:
    room = ReferencedSubject(subject_type="room", subject_key="gallery", description="A curated gallery")
    room.queue_for_generation(reason="look")

    backend = TxtOnlyBackend()
    image = process_generation_job(room, backend=backend)

    assert image["reference_count"] == 0
    assert image["reference_fallback_used"] is True
    assert "Reference context:" in image["prompt"]
    assert "brass lantern" in image["prompt"]


class ClutteredReferencedSubject(SceneImageMixin):
    max_reference_images = 2

    def collect_reference_images(self):
        return [
            {"path": "generated/cup.png", "role": "object", "caption": "wooden cup", "weight": 0.1, "notable": False},
            {"path": "generated/throne.png", "role": "object", "caption": "golden throne", "weight": 0.95, "notable": True},
            {"path": "generated/banner.png", "role": "object", "caption": "war banner", "weight": 0.7, "notable": True},
            {"path": "generated/table.png", "role": "object", "caption": "old table", "weight": 0.2, "notable": True},
        ]


def test_non_notable_references_are_excluded_and_limit_applies() -> None:
    room = ClutteredReferencedSubject(subject_type="room", subject_key="hall", description="A cluttered hall")
    room.queue_for_generation(reason="look")
    backend = RequestCapturingBackend()

    image = process_generation_job(room, backend=backend)

    assert image["reference_count"] == 2
    assert backend.last_request is not None
    captions = [ref.caption for ref in backend.last_request.reference_images]
    assert "wooden cup" not in captions
    assert captions == ["golden throne", "war banner"]


def test_non_notable_references_are_excluded_in_prompt_fallback() -> None:
    room = ClutteredReferencedSubject(subject_type="room", subject_key="hall", description="A cluttered hall")
    room.queue_for_generation(reason="look")

    image = process_generation_job(room, backend=TxtOnlyBackend())

    assert image["reference_count"] == 0
    assert image["reference_fallback_used"] is True
    assert "golden throne" in image["prompt"]
    assert "war banner" in image["prompt"]
    assert "wooden cup" not in image["prompt"]


class MalformedReferencedSubject(SceneImageMixin):
    def collect_reference_images(self):
        return [
            None,
            "not-a-dict",
            {"role": "object", "caption": "missing path"},
            {"path": "generated/valid.png", "role": "object", "caption": "valid ref"},
        ]


def test_malformed_reference_entries_are_ignored_for_multi_reference_backends() -> None:
    room = MalformedReferencedSubject(subject_type="room", subject_key="workshop", description="A busy workshop")
    room.queue_for_generation(reason="look")
    backend = RequestCapturingBackend()

    image = process_generation_job(room, backend=backend)

    assert image["reference_count"] == 1
    assert backend.last_request is not None
    assert [ref.caption for ref in backend.last_request.reference_images] == ["valid ref"]


def test_malformed_reference_entries_are_ignored_in_prompt_fallback() -> None:
    room = MalformedReferencedSubject(subject_type="room", subject_key="workshop", description="A busy workshop")
    room.queue_for_generation(reason="look")

    image = process_generation_job(room, backend=TxtOnlyBackend())

    assert image["reference_count"] == 0
    assert image["reference_fallback_used"] is True
    assert "valid ref" in image["prompt"]
    assert "missing path" not in image["prompt"]


def test_txt2img_fallback_includes_continuity_hint_when_prior_image_exists() -> None:
    room = SceneImageMixin(subject_type="room", subject_key="forest", description="A dark forest")
    room.queue_for_generation(reason="look")
    process_generation_job(room, PlaceholderBackend())
    room.mark_image_stale(reason="updated")
    room.queue_for_generation(reason="look")

    backend = TxtOnlyBackend()
    image = process_generation_job(room, backend=backend)

    assert image["mode"] == "txt2img"
    assert image["reference_fallback_used"] is False
    assert image["continuity_fallback_used"] is True
    assert "Continuity/style hint" in image["prompt"]



def test_build_generation_queue_defaults_to_unbounded_queue() -> None:
    queue = build_generation_queue()

    assert queue.max_pending is None


def test_build_generation_queue_applies_max_pending_limit() -> None:
    queue = build_generation_queue({"max_pending": 2})

    assert queue.max_pending == 2
    assert queue.enqueue_with_status("room-1") == "queued"
    assert queue.enqueue_with_status("room-2") == "queued"
    assert queue.enqueue_with_status("room-3") == "full"


def test_build_generation_queue_rejects_invalid_config_shapes() -> None:
    for invalid in ([], "x", 1):
        try:
            build_generation_queue(invalid)  # type: ignore[arg-type]
        except ValueError as err:
            assert "configuration" in str(err).lower()
        else:
            raise AssertionError("Expected ValueError for non-dict queue config")


def test_build_generation_queue_rejects_invalid_max_pending_type() -> None:
    for invalid in ("2", 1.5, object(), True, False):
        try:
            build_generation_queue({"max_pending": invalid})
        except ValueError as err:
            assert "max_pending" in str(err)
        else:
            raise AssertionError("Expected ValueError for invalid max_pending type")


def test_build_generation_queue_rejects_unknown_options() -> None:
    try:
        build_generation_queue({"max_pending": 2, "burst_limit": 10})
    except ValueError as err:
        assert "Unknown queue option" in str(err)
        assert "burst_limit" in str(err)
    else:
        raise AssertionError("Expected ValueError for unknown queue option")
