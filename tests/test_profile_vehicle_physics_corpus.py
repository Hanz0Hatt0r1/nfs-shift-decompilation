from pathlib import Path

from tools import profile_vehicle_physics_corpus as runtime


def test_has_base_physics_requires_cdf_and_edf(monkeypatch, tmp_path: Path):
    class Entry:
        def __init__(self, path):
            self.path = path

    class Archive:
        def __init__(self, entries):
            self.entries = entries

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(
        runtime,
        "BFF",
        lambda _path: Archive(
            [
                Entry("vehicles/physics/chassis/car.cdf"),
                Entry("vehicles/physics/engines/car.edf"),
            ]
        ),
    )
    assert runtime._has_base_physics(tmp_path / "car.bff") is True


def test_has_base_physics_rejects_cockpit_only_archive(monkeypatch, tmp_path: Path):
    class Entry:
        def __init__(self, path):
            self.path = path

    class Archive:
        entries = [
            Entry("vehicles/cockpit/car.dds"),
            Entry("vehicles/physics/engines/car.edf"),
        ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(runtime, "BFF", lambda _path: Archive())
    assert runtime._has_base_physics(tmp_path / "cockpit.bff") is False


def test_profile_reports_skipped_archives(monkeypatch, tmp_path: Path):
    archive = tmp_path / "cockpit.bff"
    archive.write_bytes(b"fixture")

    monkeypatch.setattr(runtime, "_materialize_bffs", lambda _inputs, _stack: [archive])
    monkeypatch.setattr(runtime, "_has_base_physics", lambda _path: False)

    report = runtime.profile_vehicle_physics_corpus([archive])

    assert report["input_count"] == 1
    assert report["selected_archive_count"] == 0
    assert report["decoded_archive_count"] == 0
    assert report["skipped"] == [
        {
            "archive": "cockpit.bff",
            "reason": "no-base-physics-cdf-edf",
        }
    ]
    assert report["ready"] is False
