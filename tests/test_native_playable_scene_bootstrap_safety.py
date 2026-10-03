from __future__ import annotations

from pathlib import Path

import native_playable_scene_bootstrap as mod


def test_overlap_guard_never_writes_into_track_scene_set(tmp_path: Path):
    track = tmp_path / "track-scene"
    track.mkdir()
    sentinel = track / "sentinel.txt"
    sentinel.write_text("keep\n", encoding="utf-8")

    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip"],
        track,
        track,
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert report["blocking_reasons"] == [
        "playable-scene-bootstrap:output-overlaps-track-scene-set"
    ]
    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    assert not (track / "playable_scene_bootstrap.json").exists()
