from pathlib import Path

from tools import audit_bff_content_reuse as runtime


def test_cross_archive_groups_include_payloads_used_at_different_paths():
    index = {
        "sha_groups": [
            {
                "sha256": "abc",
                "occurrences": 3,
                "archives": ["A.bff", "B.bff", "C.bff"],
                "paths": [
                    "render/shaders/common.fxo",
                    "render/shaders/variant.fxo",
                ],
            },
        ]
    }

    groups = runtime._cross_archive_sha_groups(index, minimum_archives=2)

    assert groups == [
        {
            "sha256": "abc",
            "archive_count": 3,
            "occurrence_count": 3,
            "unique_path_count": 2,
            "extensions": [".fxo"],
            "archives": ["A.bff", "B.bff", "C.bff"],
            "paths": [
                "render/shaders/common.fxo",
                "render/shaders/variant.fxo",
            ],
        }
    ]


def test_cross_archive_groups_respect_minimum_archive_gate():
    index = {
        "sha_groups": [
            {
                "sha256": "abc",
                "occurrences": 2,
                "archives": ["A.bff", "B.bff"],
                "paths": ["a.dds"],
            },
        ]
    }

    assert runtime._cross_archive_sha_groups(index, minimum_archives=3) == []


def test_audit_content_reuse_uses_raw_payload_identity(monkeypatch, tmp_path: Path):
    paths = [tmp_path / "A.bff", tmp_path / "B.bff"]

    class Entry:
        def __init__(self, index, path):
            self.index = index
            self.path = path
            self.type = 2
            self.compressed_size = 4
            self.uncompressed_size = 8

    class Archive:
        entries_by_name = {
            "A.bff": [Entry(0, "render/shaders/a.fxo")],
            "B.bff": [Entry(0, "render/shaders/renamed.fxo")],
        }

        def __init__(self, path):
            self.path = path
            self.entries = self.entries_by_name[path.name]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raw_payload(self, _entry):
            return b"same"

    monkeypatch.setattr(runtime, "_materialize_bffs", lambda _inputs, _stack: paths)
    monkeypatch.setattr(runtime, "BFF", Archive)

    report = runtime.audit_content_reuse(paths)

    assert report["archive_count"] == 2
    assert report["entry_count"] == 2
    assert report["unique_raw_payloads"] == 1
    assert report["summary"]["cross_archive_raw_payload_groups"] == 1
    assert report["groups"][0]["archive_count"] == 2
    assert report["groups"][0]["unique_path_count"] == 2
    assert report["groups"][0]["extensions"] == [".fxo"]
