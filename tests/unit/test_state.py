from __future__ import annotations

import pytest

from evennia_ai_image_generator.state import ImageLifecycle


def _record(revision: int) -> dict:
    return {
        "image_id": f"room_1_{revision:04d}",
        "path": f"rooms/1/{revision:04d}.png",
        "url": f"https://game.test/{revision:04d}.png",
        "revision": revision,
        "state_fingerprint": f"fp-{revision}",
        "prompt": f"prompt {revision}",
    }


def test_trim_history_keeps_newest_entries_and_rebuilds_index() -> None:
    lifecycle = ImageLifecycle(max_history=3)

    for revision in range(1, 6):
        lifecycle.state = "pending"
        lifecycle.set_ready(_record(revision))
        lifecycle.mark_stale(reason="update")

    assert [entry["revision"] for entry in lifecycle.image_history] == [3, 4, 5]
    assert set(lifecycle.image_index.keys()) == {"fp-3", "fp-4", "fp-5"}


def test_trim_history_returns_removed_count() -> None:
    lifecycle = ImageLifecycle()
    lifecycle.image_history = [_record(1), _record(2), _record(3)]
    lifecycle.image_index = {f"fp-{i}": {"revision": i} for i in range(1, 4)}
    lifecycle.image_current = _record(3)

    removed = lifecycle.trim_history(max_entries=2)

    assert removed == 1
    assert [entry["revision"] for entry in lifecycle.image_history] == [2, 3]
    assert set(lifecycle.image_index.keys()) == {"fp-2", "fp-3"}


def test_set_ready_requires_pending() -> None:
    lifecycle = ImageLifecycle()
    with pytest.raises(ValueError, match="Can only set ready"):
        lifecycle.set_ready(_record(1))


def test_trim_history_zero_limit_clears_history_and_index() -> None:
    lifecycle = ImageLifecycle()
    lifecycle.image_history = [_record(1), _record(2)]
    lifecycle.image_index = {"fp-1": {"revision": 1}, "fp-2": {"revision": 2}}
    lifecycle.image_current = None

    removed = lifecycle.trim_history(max_entries=0)

    assert removed == 2
    assert lifecycle.image_history == []
    assert lifecycle.image_index == {}


def test_trim_history_zero_limit_clears_index_even_with_current_image() -> None:
    lifecycle = ImageLifecycle()
    lifecycle.image_history = [_record(1), _record(2)]
    lifecycle.image_index = {"fp-1": {"revision": 1}, "fp-2": {"revision": 2}}
    lifecycle.image_current = _record(2)

    removed = lifecycle.trim_history(max_entries=0)

    assert removed == 2
    assert lifecycle.image_history == []
    assert lifecycle.image_index == {}


@pytest.mark.parametrize("invalid", [True, False, 1.5, "3", -1])
def test_lifecycle_rejects_invalid_max_history_values(invalid) -> None:
    with pytest.raises(ValueError, match="max_history"):
        ImageLifecycle(max_history=invalid)
