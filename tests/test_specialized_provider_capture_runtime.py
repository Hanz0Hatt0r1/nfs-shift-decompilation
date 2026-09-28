import pytest

import specialized_provider_capture_runtime as runtime
from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout


@pytest.mark.parametrize("provider_id", [0, 1])
def test_build_provider_capture_payload_uses_exact_layout(provider_id):
    layout = get_storage_layout(provider_id)
    payload = runtime.build_provider_capture_payload(
        provider_id=provider_id,
        stage="pre-solve-provider",
        workspace=[0.0] * layout.factor_workspace_doubles,
        output_vector=[0.0] * layout.output_vector_doubles,
    )

    assert payload["provider_id"] == provider_id
    assert payload["workspace_doubles"] == layout.factor_workspace_doubles
    assert payload["scalar_count"] == layout.scalar_count
    assert payload["row_pointers"] == list(get_row_pointers(provider_id))


def test_normalize_provider_capture_rejects_wrong_workspace_length():
    layout = get_storage_layout(0)

    with pytest.raises(ValueError, match="workspace length"):
        runtime.normalize_provider_capture(
            {
                "provider_id": 0,
                "stage": "pre-solve-provider",
                "workspace": [],
                "output_vector": [0.0] * layout.output_vector_doubles,
            }
        )


def test_normalize_provider_capture_rejects_wrong_output_length():
    layout = get_storage_layout(1)

    with pytest.raises(ValueError, match="output_vector length"):
        runtime.normalize_provider_capture(
            {
                "provider_id": 1,
                "stage": "post-solve-provider",
                "workspace": [0.0] * layout.factor_workspace_doubles,
                "output_vector": [],
            }
        )


def test_compare_provider_geometry_accepts_static_pointer_table():
    layout = get_storage_layout(0)
    capture = runtime.build_provider_capture_payload(
        provider_id=0,
        stage="pre-solve-provider",
        workspace=[0.0] * layout.factor_workspace_doubles,
        output_vector=[0.0] * layout.output_vector_doubles,
    )

    result = runtime.compare_provider_geometry(capture, provider_id=0)

    assert result["ready"] is True
    assert result["row_pointer_mismatch_count"] == 0
    assert result["solve_function"] == hex(0x007C7200)


def test_compare_provider_geometry_detects_pointer_mismatch():
    layout = get_storage_layout(1)
    pointers = list(get_row_pointers(1))
    pointers[2] += 8
    capture = runtime.build_provider_capture_payload(
        provider_id=1,
        stage="post-solve-provider",
        workspace=[0.0] * layout.factor_workspace_doubles,
        output_vector=[0.0] * layout.output_vector_doubles,
        row_pointers=pointers,
    )

    result = runtime.compare_provider_geometry(capture, provider_id=1)

    assert result["ready"] is False
    assert "row-pointer-table-mismatch" in result["errors"]
    assert result["row_pointer_mismatch_count"] == 1


def test_describe_contract_contains_both_provider_domains():
    contract = runtime.describe_provider_capture_contract()

    assert [item["provider_id"] for item in contract["providers"]] == [0, 1]
    assert contract["providers"][0]["scalar_count"] == 40
    assert contract["providers"][1]["scalar_count"] == 34
    assert contract["status"] == "source-backed-provider-capture-schema"
