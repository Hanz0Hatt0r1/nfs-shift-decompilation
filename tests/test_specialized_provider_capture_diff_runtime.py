import pytest

import specialized_provider_capture_diff_runtime as runtime
from specialized_provider_capture_runtime import build_provider_capture_payload
from specialized_provider_storage_runtime import get_storage_layout


def _capture(provider_id: int, workspace_value: float, output_value: float):
    layout = get_storage_layout(provider_id)
    return build_provider_capture_payload(
        provider_id=provider_id,
        stage="pre-solve-provider",
        workspace=[workspace_value] * layout.factor_workspace_doubles,
        output_vector=[output_value] * layout.output_vector_doubles,
        row_pointers=[],
        frame_index=1,
    )


def test_compare_provider_captures_detects_workspace_and_output_changes():
    layout = get_storage_layout(0)
    before = _capture(0, 0.0, 0.0)
    after = _capture(0, 0.0, 0.0)

    after["workspace"][3] = 2.5
    after["output_vector"][4] = -1.25

    result = runtime.compare_provider_captures(before, after)

    assert result["ready"] is True
    assert result["workspace_change_count"] == 1
    assert result["output_change_count"] == 1
    assert result["changed_address_count"] == 2
    assert hex(layout.factor_workspace_base + 3 * 8) in result["changed_addresses"]
    assert hex(layout.output_vector_base + 4 * 8) in result["changed_addresses"]


def test_compare_provider_captures_tolerates_small_changes():
    before = _capture(1, 0.0, 0.0)
    after = _capture(1, 0.0, 0.0)
    after["workspace"][0] = 1e-13
    after["output_vector"][0] = 1e-13

    result = runtime.compare_provider_captures(
        before,
        after,
        abs_tol=1e-12,
    )

    assert result["workspace_change_count"] == 0
    assert result["output_change_count"] == 0


def test_compare_provider_captures_rejects_provider_mismatch():
    before = _capture(0, 0.0, 0.0)
    after = _capture(1, 0.0, 0.0)

    with pytest.raises(ValueError):
        runtime.compare_provider_captures(before, after)


def test_compare_provider_captures_detects_row_pointer_mutation():
    before = _capture(0, 0.0, 0.0)
    after = _capture(0, 0.0, 0.0)
    after["row_pointers"][1] += 8

    result = runtime.compare_provider_captures(before, after)

    assert result["ready"] is False
    assert "row-pointer-table-mutated" in result["errors"]


def test_validate_capture_diff_checks_changed_address_count():
    result = runtime.validate_provider_capture_diff(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "workspace_changes": [],
            "output_changes": [],
            "changed_addresses": ["0x1000"],
            "changed_address_count": 0,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "changed-address-count-mismatch" in result["errors"]


def test_summarize_capture_diff():
    result = runtime.summarize_provider_capture_diff(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "workspace_change_count": 7,
            "output_change_count": 3,
            "changed_address_count": 10,
            "status": "matched-shape",
            "ready": True,
        }
    )

    assert result == {
        "provider_id": 1,
        "scalar_count": 34,
        "workspace_change_count": 7,
        "output_change_count": 3,
        "changed_address_count": 10,
        "status": "matched-shape",
        "ready": True,
    }
