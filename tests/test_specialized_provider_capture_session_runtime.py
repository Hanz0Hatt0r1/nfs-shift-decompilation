import pytest

import specialized_provider_capture_session_runtime as runtime


def _capture(provider_id: int, frame_index: int = 1):
    if provider_id == 0:
        workspace = [0.0] * 1190
        output = [0.0] * 40
    else:
        workspace = [0.0] * 746
        output = [0.0] * 34

    return {
        "provider_id": provider_id,
        "stage": "pre-solve-provider",
        "workspace": workspace,
        "output_vector": output,
        "row_pointers": [],
        "frame_index": frame_index,
    }


def test_normalize_provider_session_accepts_matching_provider_frames():
    pre = _capture(0, 7)
    post = _capture(0, 7)
    post["stage"] = "post-solve-provider"

    result = runtime.normalize_provider_session(pre, post)

    assert result["ready"] is True
    assert result["provider_id"] == 0
    assert result["scalar_count"] == 40
    assert result["errors"] == []


def test_normalize_provider_session_rejects_frame_mismatch():
    pre = _capture(1, 7)
    post = _capture(1, 8)

    with pytest.raises(ValueError):
        # normalize_provider_capture rejects nothing here; the mismatch is in
        # the returned session, so validate the session result explicitly.
        pass

    result = runtime.normalize_provider_session(pre, post)
    assert result["ready"] is False
    assert "frame-index-mismatch" in result["errors"]


def test_validate_provider_session_checks_provider_and_scalar_domain():
    result = runtime.validate_provider_session(
        {
            "provider_id": 2,
            "scalar_count": 0,
            "geometry": {
                "pre": {"scalar_count": 0},
            },
            "session": {
                "post_solve": None,
            },
            "mutation_diff": None,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "unsupported-provider-id" in result["errors"]
    assert "non-positive-scalar-count" in result["errors"]


def test_validate_provider_session_checks_mutation_shape():
    result = runtime.validate_provider_session(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "geometry": {
                "pre": {"scalar_count": 40},
                "post": None,
            },
            "session": {
                "post_solve": None,
            },
            "mutation_diff": {
                "provider_id": 1,
                "scalar_count": 34,
            },
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "mutation-provider-id-mismatch" in result["errors"]
    assert "mutation-scalar-count-mismatch" in result["errors"]


def test_summarize_provider_session():
    result = runtime.summarize_provider_session(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "session": {
                "post_solve": {},
            },
            "mutation_diff": {
                "workspace_change_count": 100,
                "output_change_count": 20,
            },
            "reset_delta": {
                "counts": {
                    "reset-zero-slot-deviation": 30,
                    "reset-unit-slot-deviation": 4,
                    "outside-reset-domain-nonzero": 50,
                    "output-nonzero": 2,
                }
            },
            "ready": True,
        }
    )

    assert result["workspace_changes"] == 100
    assert result["output_changes"] == 20
    assert result["reset_zero_slot_deviations"] == 30
    assert result["reset_unit_slot_deviations"] == 4
    assert result["outside_reset_domain_nonzero"] == 50
    assert result["output_nonzero_before_solve"] == 2


def test_build_provider_session_contract_requires_valid_provider_capture():
    pre = _capture(0, 1)
    report = runtime.build_provider_session_contract(pre)

    assert report["ready"] is True
    assert report["geometry"]["pre"]["ready"] is True
    assert report["mutation_diff"] is None
