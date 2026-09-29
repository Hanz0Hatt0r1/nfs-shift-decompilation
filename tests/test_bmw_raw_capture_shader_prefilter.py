import hashlib
import json

from bmw_raw_capture_shader_prefilter import (
    FORMAT,
    prefilter_bmw_raw_capture,
    validate_files,
)


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
VS_SHA = hashlib.sha256(VS).hexdigest()
PS_SHA = hashlib.sha256(PS).hexdigest()
PAIR_SHA = hashlib.sha256(VS + PS).hexdigest()


def _target_set(*, strength="exact-pair"):
    target = {
        "identity_kind": (
            "pair" if strength == "exact-pair" else "pixel"
        ),
        "identity_value": (
            PAIR_SHA if strength == "exact-pair" else PS_SHA
        ),
        "strength": strength,
        "permutation_identity_sha256": None,
        "pair_byte_sha256": PAIR_SHA,
        "vertex_byte_sha256": VS_SHA,
        "pixel_byte_sha256": PS_SHA,
    }
    return {
        "format": "SHIFT.BMWRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "primitive_targets": [
            {
                "primitive_index": 3,
                "material_ref": "vehicles/bmw/windows.mtx",
                "draw_range": {
                    "first_index": 13830,
                    "index_count": 612,
                    "primitive_count": 204,
                },
                "targets": [target],
            }
        ],
    }


def _events():
    return [
        {
            "event": "create_vertex_shader",
            "frame": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        },
        {
            "event": "create_pixel_shader",
            "frame": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        },
        {
            "event": "set_vertex_shader",
            "frame": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        },
        {
            "event": "set_pixel_shader",
            "frame": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        },
        {
            "event": "draw_indexed_primitive",
            "event_index": 9,
            "frame": 1,
            "device_ptr": "0x1",
            "start_index": 13830,
            "primitive_count": 204,
        },
    ]


def test_raw_prefilter_finds_exact_active_pair_on_canonical_draw():
    report = prefilter_bmw_raw_capture(
        _target_set(),
        _events(),
    )

    assert report["format"] == FORMAT
    assert report["coverage_ready"] is True
    assert report["summary"]["covered_primitive_count"] == 1
    assert report["summary"]["strong_pair_primitive_count"] == 1
    row = report["primitive_results"][0]
    assert row["best_score"] == 90
    assert row["strong_pair_observed"] is True
    assert row["matches"][0]["pair_byte_sha256"] == PAIR_SHA
    assert row["matches"][0]["evidence"] == ["pair_byte_sha256"]
    assert report["boundary"]["same_instance_proven"] is False


def test_raw_prefilter_keeps_prefilter_only_target_weak():
    report = prefilter_bmw_raw_capture(
        _target_set(strength="prefilter-only"),
        _events(),
    )

    assert report["coverage_ready"] is True
    assert report["summary"]["strong_pair_primitive_count"] == 0
    assert report["primitive_results"][0]["best_score"] == 40
    assert report["primitive_results"][0]["strong_pair_observed"] is False


def test_raw_prefilter_requires_exact_draw_range():
    events = _events()
    events[-1]["start_index"] = 13831
    report = prefilter_bmw_raw_capture(_target_set(), events)

    assert report["coverage_ready"] is False
    assert report["status"] == "not-found"
    assert report["summary"]["covered_primitive_count"] == 0


def test_raw_prefilter_reports_target_shader_creation_hits():
    report = prefilter_bmw_raw_capture(_target_set(), _events())

    assert report["summary"]["target_shader_creation_hit_count"] == 2
    assert {
        row["stage"] for row in report["shader_creation_hits"]
    } == {"vertex", "pixel"}


def test_raw_prefilter_fails_closed_on_shader_pointer_reuse():
    events = _events()
    events.insert(1, {
        "event": "create_vertex_shader",
        "frame": 1,
        "device_ptr": "0x1",
        "shader_ptr": "0x10",
        "bytes_hex": bytes.fromhex("0000feff03000000").hex(),
    })
    report = prefilter_bmw_raw_capture(_target_set(), events)

    assert report["coverage_ready"] is False
    assert any(
        reason.endswith(":vertex-shader-pointer-reused")
        for reason in report["blocking_reasons"]
    )


def test_raw_prefilter_rejects_invalid_shader_hex():
    events = _events()
    events[0]["bytes_hex"] = "not-hex"
    report = prefilter_bmw_raw_capture(_target_set(), events)

    assert report["coverage_ready"] is False
    assert any(
        reason.endswith(":vertex-shader-create-invalid")
        for reason in report["blocking_reasons"]
    )


def test_raw_prefilter_jsonl_loader_blocks_invalid_line(tmp_path):
    target = tmp_path / "targets.json"
    capture = tmp_path / "capture.jsonl"
    target.write_text(json.dumps(_target_set()), encoding="utf-8")
    capture.write_text(
        json.dumps(_events()[0]) + "\n" + "{bad json}\n",
        encoding="utf-8",
    )

    report = validate_files(target, capture)

    assert report["coverage_ready"] is False
    assert report["status"] == "blocked"
    assert "raw-prefilter:line-2:json-invalid" in report["blocking_reasons"]


def test_raw_prefilter_rejects_wrong_target_format():
    try:
        prefilter_bmw_raw_capture({"format": "wrong"}, [])
    except ValueError as error:
        assert "BMWRuntimeShaderTargetSet" in str(error)
    else:
        raise AssertionError("wrong target format must be rejected")
