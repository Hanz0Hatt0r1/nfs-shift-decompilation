import hashlib
import json

from imb_raw_capture_shader_prefilter import (
    FORMAT,
    prefilter_imb_raw_capture,
    validate_files,
)


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
OTHER_PS = bytes.fromhex("0000ffff03000000")
VS_SHA = hashlib.sha256(VS).hexdigest()
PS_SHA = hashlib.sha256(PS).hexdigest()
PAIR_SHA = hashlib.sha256(VS + PS).hexdigest()


def _target_set(*, exact_pair=False, capture_ready=True):
    if exact_pair:
        target = {
            "identity_kind": "pair",
            "identity_value": PAIR_SHA,
            "strength": "exact-pair",
            "pair_byte_sha256": PAIR_SHA,
            "vertex_byte_sha256": VS_SHA,
            "pixel_byte_sha256": PS_SHA,
            "binding_indices": [3, 7],
            "shader_families": ["basicinstanced"],
        }
    else:
        target = {
            "identity_kind": "pixel",
            "identity_value": PS_SHA,
            "strength": "prefilter-only",
            "pair_byte_sha256": PAIR_SHA,
            "vertex_byte_sha256": VS_SHA,
            "pixel_byte_sha256": PS_SHA,
            "binding_indices": [3, 7],
            "shader_families": ["basicinstanced"],
        }
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "capture_ready": capture_ready,
        "binding_target_count": 10,
        "unique_targets": [target],
    }


def _events(pixel=PS):
    return [
        {
            "event": "create_vertex_shader",
            "frame": 4,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        },
        {
            "event": "create_pixel_shader",
            "frame": 4,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": pixel.hex(),
        },
        {
            "event": "set_vertex_shader",
            "frame": 4,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        },
        {
            "event": "set_pixel_shader",
            "frame": 4,
            "event_index": 4,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        },
        {
            "event": "draw_indexed_primitive",
            "frame": 4,
            "event_index": 5,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "min_vertex_index": 0,
            "num_vertices": 100,
            "start_index": 200,
            "primitive_count": 12,
        },
    ]


def test_prefilter_keeps_draw_with_target_pixel_hash():
    report = prefilter_imb_raw_capture(
        _target_set(),
        _events(),
    )

    assert report["format"] == FORMAT
    assert report["status"] == "matched"
    assert report["prefilter_ready"] is True
    assert report["summary"]["candidate_draw_count"] == 1
    assert report["summary"]["observed_target_hash_count"] == 1
    assert report["summary"]["candidate_binding_index_count"] == 2

    draw = report["candidate_draws"][0]
    assert draw["frame"] == 4
    assert draw["event_index"] == 5
    assert draw["draw_ordinal"] == 1
    assert draw["pixel_byte_sha256"] == PS_SHA
    assert draw["candidate_binding_indices"] == [3, 7]
    assert draw["shader_families"] == ["basicinstanced"]
    assert draw["matches"][0]["score"] == 40
    assert draw["matches"][0]["evidence"] == ["pixel_byte_sha256"]
    assert report["boundary"]["same_instance_proven"] is False
    assert report["boundary"]["draw_range_identity_proven"] is False


def test_prefilter_exact_pair_target_scores_pair_without_attribution_claim():
    report = prefilter_imb_raw_capture(
        _target_set(exact_pair=True),
        _events(),
    )

    draw = report["candidate_draws"][0]
    assert draw["pair_byte_sha256"] == PAIR_SHA
    assert draw["matches"][0]["score"] == 90
    assert draw["matches"][0]["evidence"] == ["pair_byte_sha256"]
    assert report["boundary"]["selects_permutation"] is False


def test_non_target_shader_produces_no_candidate_draw():
    report = prefilter_imb_raw_capture(
        _target_set(),
        _events(pixel=OTHER_PS),
    )

    assert report["prefilter_ready"] is True
    assert report["status"] == "not-found"
    assert report["summary"]["candidate_draw_count"] == 0
    assert report["summary"]["observed_target_hash_count"] == 0


def test_target_shader_creation_hit_is_preserved_before_draw():
    report = prefilter_imb_raw_capture(_target_set(), _events())

    assert report["summary"]["target_shader_creation_hit_count"] == 2
    hits = report["shader_creation_hits"]
    assert {row["stage"] for row in hits} == {"vertex", "pixel"}


def test_shader_pointer_reuse_is_explicit_blocker():
    events = _events()
    events.insert(1, {
        "event": "create_vertex_shader",
        "frame": 4,
        "event_index": 6,
        "device_ptr": "0x1",
        "shader_ptr": "0x10",
        "bytes_hex": bytes.fromhex("0000feff09000000").hex(),
    })
    report = prefilter_imb_raw_capture(_target_set(), events)

    assert report["prefilter_ready"] is False
    assert report["status"] == "blocked"
    assert any(
        reason.endswith(":vertex-shader-pointer-reused")
        for reason in report["blocking_reasons"]
    )


def test_target_set_not_capture_ready_blocks_prefilter():
    report = prefilter_imb_raw_capture(
        _target_set(capture_ready=False),
        _events(),
    )

    assert report["prefilter_ready"] is False
    assert report["status"] == "blocked"
    assert (
        "imb-raw-prefilter:target-set-not-capture-ready"
        in report["blocking_reasons"]
    )


def test_jsonl_loader_blocks_invalid_line(tmp_path):
    target = tmp_path / "targets.json"
    capture = tmp_path / "capture.jsonl"
    target.write_text(json.dumps(_target_set()), encoding="utf-8")
    capture.write_text(
        json.dumps(_events()[0]) + "\n" + "{bad json}\n",
        encoding="utf-8",
    )

    report = validate_files(target, capture)

    assert report["prefilter_ready"] is False
    assert report["status"] == "blocked"
    assert (
        "imb-raw-prefilter:line-2:json-invalid"
        in report["blocking_reasons"]
    )


def test_wrong_target_format_is_rejected():
    try:
        prefilter_imb_raw_capture({"format": "wrong"}, [])
    except ValueError as error:
        assert "IMBRuntimeShaderTargetSet" in str(error)
    else:
        raise AssertionError("wrong target format must be rejected")
