import pytest

import specialized_provider_reset_delta_runtime as runtime


def test_classify_known_zero_and_unit_slots():
    kwargs = {
        "reset_domain": {0x1000, 0x1008},
        "reset_unit": {0x1000},
        "region": "workspace",
        "abs_tol": 1e-12,
        "rel_tol": 1e-12,
    }

    assert runtime._classify_change(
        0x1008,
        0.5,
        expected=0.0,
        **kwargs,
    ) == "reset-zero-slot-deviation"

    assert runtime._classify_change(
        0x1000,
        0.5,
        expected=1.0,
        **kwargs,
    ) == "reset-unit-slot-deviation"


def test_classify_unknown_workspace_nonzero():
    result = runtime._classify_change(
        0x2000,
        3.0,
        expected=None,
        reset_domain=set(),
        reset_unit=set(),
        region="workspace",
        abs_tol=0.0,
        rel_tol=0.0,
    )

    assert result == "outside-reset-domain-nonzero"


def test_classify_output_nonzero():
    result = runtime._classify_change(
        0x3000,
        -2.0,
        expected=0.0,
        reset_domain=set(),
        reset_unit=set(),
        region="output",
        abs_tol=0.0,
        rel_tol=0.0,
    )

    assert result == "output-nonzero"


def test_compare_capture_to_reset_rejects_provider_mismatch():
    with pytest.raises(ValueError):
        runtime.compare_capture_to_reset(
            "",
            {
                "provider_id": 1,
                "stage": "pre-solve-provider",
                "workspace": [0.0] * 1190,
                "output_vector": [0.0] * 40,
            },
            provider_id=0,
        )


def test_summarize_reset_delta():
    result = runtime.summarize_reset_delta(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "capture_stage": "pre-solve-provider",
            "reset_domain_workspace_slots": 370,
            "reset_domain_output_slots": 40,
            "counts": {
                "reset-zero-slot-deviation": 12,
                "reset-unit-slot-deviation": 2,
                "outside-reset-domain-nonzero": 21,
                "output-nonzero": 4,
            },
            "reset_state_equivalent": False,
            "ready": True,
        }
    )

    assert result["reset_zero_slot_deviations"] == 12
    assert result["reset_unit_slot_deviations"] == 2
    assert result["outside_reset_domain_nonzero"] == 21
    assert result["output_nonzero"] == 4
    assert result["reset_state_equivalent"] is False


def test_validate_reset_delta_checks_output_domain():
    result = runtime.validate_reset_delta(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_domain_output_slots": 33,
            "categories": {},
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "output-reset-domain-count-mismatch" in result["errors"]


def test_validate_reset_delta_accepts_finite_values():
    result = runtime.validate_reset_delta(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "reset_domain_output_slots": 34,
            "categories": {
                "reset-zero-slot-deviation": [
                    {"address": "0x1000", "observed": 1.0}
                ],
            },
            "errors": [],
        }
    )

    assert result["ready"] is True


def test_reset_delta_retains_cleanup_mismatch_as_metadata():
    result = runtime.summarize_reset_delta(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "cleanup_reset_equivalent": False,
            "reset_state_equivalent": True,
            "counts": {},
            "ready": True,
        }
    )

    assert result["ready"] is True
    assert result["provider_id"] == 1
