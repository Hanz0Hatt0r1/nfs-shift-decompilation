from bmt_render_state_corpus import (
    FORMAT,
    build_corpus_report,
)


def _enum(raw, index):
    return {
        "raw": raw,
        "engine_enum_index": index,
        "status": "known",
    }


def _record(path, sha, *, alpha_test=None, blend=None, depth=None):
    return {
        "archive": "fixture.bff",
        "path": path,
        "payload_sha256": sha,
        "material": {
            "cull": "EBFCT_ANTICLOCKWISE",
            "render_state": {
                "format": "SHIFT.BMTRenderState/1",
                "depth": depth,
                "alpha_test": alpha_test,
                "alpha_blend": blend,
            },
        },
    }


def test_corpus_deduplicates_decoded_payloads_and_counts_state():
    alpha = {
        "format": "SHIFT.BMTAlphaTestState/1",
        "enabled": True,
        "function": _enum("ETF_GREATER_THAN_OR_EQUAL", 6),
        "value_raw": 64.0,
        "value_normalized": 64.0 / 255.0,
    }
    blend = {
        "format": "SHIFT.BMTAlphaBlendState/1",
        "enabled": True,
        "source_blend": _enum("EBF_SOURCE_ALPHA", 4),
        "dest_blend": _enum("EBF_INV_SOURCE_ALPHA", 5),
        "blend_op": _enum("EBO_ADD", 0),
    }
    depth = {
        "format": "SHIFT.BMTDepthState/1",
        "enabled": True,
        "write_enabled": False,
        "function": _enum("ETF_LESS_THAN_OR_EQUAL", 3),
    }
    records = [
        _record("vehicles/a/lights.bmt", "a" * 64, alpha_test=alpha),
        _record("vehicles/b/lights.bmt", "a" * 64, alpha_test=alpha),
        _record(
            "vehicles/a/window.bmt",
            "b" * 64,
            blend=blend,
            depth=depth,
        ),
    ]

    result = build_corpus_report(
        records,
        archives=[{"name": "fixture.bff", "bmt_count": 3}],
    )

    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["stats"]["bmt_instances"] == 3
    assert result["stats"]["unique_payloads"] == 2
    assert result["stats"]["duplicate_instances"] == 1
    assert result["stats"]["alpha_test_groups"] == 1
    assert result["stats"]["alpha_test_enabled"] == 1
    assert result["stats"]["blend_enabled"] == 1
    assert result["stats"]["depth_write_disabled"] == 1
    assert result["stats"]["native_ready_unique_payloads"] == 1
    assert result["stats"]["native_blocked_unique_payloads"] == 1
    assert result["alpha_test_reference_u8"] == {"64": 1}
    assert result["native_blocking_reasons"] == {
        "alpha-test:fragment-alpha-quantization-unproven": 1
    }


def test_corpus_records_decode_errors_without_hiding_observations():
    result = build_corpus_report(
        [_record("vehicles/a/paint.bmt", "c" * 64)],
        errors=[{
            "archive": "broken.bff",
            "path": "vehicles/b/broken.bmt",
            "error": "ValueError: broken",
        }],
    )
    assert result["ready"] is False
    assert result["stats"]["unique_payloads"] == 1
    assert result["stats"]["decode_errors"] == 1
    assert "bmt-corpus:decode-errors" in result["blocking_reasons"]


def test_corpus_fails_closed_on_missing_payload_identity():
    result = build_corpus_report([{
        "archive": "fixture.bff",
        "path": "vehicles/a/paint.bmt",
        "material": {},
    }])
    assert result["ready"] is False
    assert (
        "bmt-corpus:payload-sha256-missing:vehicles/a/paint.bmt"
        in result["blocking_reasons"]
    )
