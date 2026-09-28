from pathlib import Path

import specialized_provider_capture_bundle_runtime as runtime


def test_parse_snapshot_filename():
    assert runtime.parse_snapshot_filename(
        "provider_pre_0_000123.json"
    ) == {
        "stage": "pre-solve-provider",
        "provider_id": 0,
        "hit": 123,
        "filename": "provider_pre_0_000123.json",
    }

    assert runtime.parse_snapshot_filename(
        "provider_post_1_000007.json"
    ) == {
        "stage": "post-solve-provider",
        "provider_id": 1,
        "hit": 7,
        "filename": "provider_post_1_000007.json",
    }


def test_parse_snapshot_filename_rejects_unknown_names():
    assert runtime.parse_snapshot_filename("provider_bad.json") is None
    assert runtime.parse_snapshot_filename("other_0_000001.json") is None


def test_index_directory_pairs_pre_and_post(tmp_path: Path):
    for name in (
        "provider_pre_0_000001.json",
        "provider_post_0_000001.json",
        "provider_pre_1_000002.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "provider_misc.json").write_text(
        "{}",
        encoding="utf-8",
    )

    result = runtime.index_provider_snapshot_directory(tmp_path)

    assert result["bundle_count"] == 2
    assert result["ready"] is True
    assert result["ignored_file_count"] == 1
    assert result["bundles"][0]["provider_id"] == 0
    assert result["bundles"][0]["pre"]["hit"] == 1
    assert result["bundles"][0]["post"]["hit"] == 1
    assert result["bundles"][1]["provider_id"] == 1
    assert result["bundles"][1]["post"] is None


def test_index_directory_rejects_missing_pre(tmp_path: Path):
    (tmp_path / "provider_post_0_000001.json").write_text(
        "{}",
        encoding="utf-8",
    )

    result = runtime.index_provider_snapshot_directory(tmp_path)

    assert result["ready"] is False
    assert "missing-pre:0:1" in result["errors"]


def test_index_directory_rejects_duplicate_stage(tmp_path: Path):
    for suffix in ("a", "b"):
        (tmp_path / f"provider_pre_0_000001{suffix}.json").write_text(
            "{}",
            encoding="utf-8",
        )

    result = runtime.index_provider_snapshot_directory(tmp_path)

    assert result["ready"] is False
    # These names do not match the strict regex, so they are ignored rather
    # than considered duplicates.
    assert result["ignored_file_count"] == 2


def _write_capture(path: Path, provider_id: int, frame_index: int, stage: str):
    if provider_id == 0:
        workspace = [0.0] * 1190
        output = [0.0] * 40
    else:
        workspace = [0.0] * 746
        output = [0.0] * 34

    import json
    path.write_text(
        json.dumps(
            {
                "provider_id": provider_id,
                "stage": stage,
                "workspace": workspace,
                "output_vector": output,
                "row_pointers": [],
                "frame_index": frame_index,
            }
        ),
        encoding="utf-8",
    )


def test_analyze_capture_bundle_without_post(tmp_path: Path):
    pre_path = tmp_path / "provider_pre_0_000001.json"
    _write_capture(
        pre_path,
        0,
        3,
        "pre-solve-provider",
    )

    result = runtime.analyze_capture_bundle(
        {
            "provider_id": 0,
            "hit": 1,
            "pre": {"path": str(pre_path)},
            "post": None,
        }
    )

    assert result["ready"] is True
    assert result["frame_index"] == 3
    assert result["reset_events"]["pre_post_order"] is None


def test_analyze_capture_directory_reports_bundle_summary(tmp_path: Path):
    pre = tmp_path / "provider_pre_1_000001.json"
    post = tmp_path / "provider_post_1_000001.json"
    _write_capture(pre, 1, 4, "pre-solve-provider")
    _write_capture(post, 1, 4, "post-solve-provider")

    result = runtime.analyze_capture_directory(tmp_path)

    assert result["ready"] is True
    assert result["bundle_count"] == 1
    assert result["summary"]["bundle_count"] == 1
    assert result["summary"]["bundles_with_post"] == 1
