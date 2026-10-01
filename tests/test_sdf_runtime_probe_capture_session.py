from pathlib import Path

import pytest

import sdf_runtime_probe_capture_session as runtime


def test_phase643_capture_session_ids_are_normalized_hex():
    session_id = runtime.new_capture_session_id()

    assert len(session_id) == 32
    assert runtime.validate_capture_session_id(session_id.upper()) == session_id
    int(session_id, 16)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "a" * 31,
        "a" * 33,
        "g" * 32,
    ],
)
def test_phase643_capture_session_id_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="32 hexadecimal"):
        runtime.validate_capture_session_id(value)


def test_phase643_clear_capture_artifacts_preserves_non_evidence_files(
    tmp_path: Path,
):
    generated = [
        "relation_state_mutation_events.jsonl",
        "relation_state_mutation_timeline.json",
        "frame_entry_000001.json",
        "pre_solve_000001.json",
        "post_solve_000001.json",
        "provider_pre_0_000001.json",
        "provider_post_0_000001.json",
        "scalar_reset_events.jsonl",
        "provider_reset_effects.jsonl",
        "sdf_capture_evidence.zip",
    ]
    for name in generated:
        (tmp_path / name).write_text("stale\n", encoding="utf-8")

    preserved = [
        "SHIFT.exe",
        "attach.gdb",
        "probe_manifest.json",
        "notes.txt",
    ]
    for name in preserved:
        (tmp_path / name).write_text("keep\n", encoding="utf-8")

    assert [path.name for path in runtime.capture_artifact_paths(tmp_path)] == sorted(
        generated
    )

    removed = runtime.clear_capture_artifacts(tmp_path)

    assert removed == sorted(generated)
    assert runtime.capture_artifact_paths(tmp_path) == []
    for name in preserved:
        assert (tmp_path / name).is_file()


def test_phase643_capture_session_manifest_fragment_reports_cleanup():
    result = runtime.describe_capture_session(
        "ab" * 16,
        stale_artifacts_removed=["pre_solve_000002.json", "pre_solve_000001.json"],
    )

    assert result == {
        "format": runtime.FORMAT,
        "version": 1,
        "id": "ab" * 16,
        "single_session_output": True,
        "stale_artifact_count": 2,
        "stale_artifacts_removed": [
            "pre_solve_000001.json",
            "pre_solve_000002.json",
        ],
    }
