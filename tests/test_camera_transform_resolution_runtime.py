from camera_transform_resolution_runtime import (
    apply_external_camera_offset,
    resolve_camera_outputs,
    resolve_metadata,
    resolve_orientation,
    resolve_position,
)


def test_external_offset_is_added_only_after_successful_base_resolver():
    result = apply_external_camera_offset(
        base_output=[1, 2, 3],
        external_offset=[4, 5, 6],
        service_query_succeeded=True,
    )
    assert result["output"] == [5.0, 7.0, 9.0]
    failed = apply_external_camera_offset(
        base_output=[1, 2, 3],
        external_offset=[4, 5, 6],
        service_query_succeeded=False,
    )
    assert failed["output"] == [1.0, 2.0, 3.0]


def test_position_wrapper_uses_type_78_when_selector_is_six():
    result = resolve_position(
        active_target_data={"type_0x78": 4},
        target_id=2,
        type_selector=6,
        transform_payload="payload",
        service_available=True,
        fallback_position=[1, 2, 3],
        local_fallback_enabled=False,
        service_result="position",
    )
    assert result["status"] == "id-query"
    assert result["actions"][0]["arguments"][0] == 4


def test_position_wrapper_falls_back_to_local_position_for_minus_one():
    result = resolve_position(
        active_target_data={"type_0x78": 6, "fallback_id": -1},
        target_id=-1,
        type_selector=3,
        transform_payload="payload",
        service_available=True,
        fallback_position=[1, 2, 3],
        local_fallback_enabled=True,
    )
    assert result["status"] == "local-fallback"


def test_orientation_wrapper_forwards_type_and_payload():
    result = resolve_orientation(
        active_target_data={"type_0x78": 5},
        target_id=3,
        type_selector=6,
        value="q",
        service_available=True,
        service_result="orientation",
    )
    assert result["status"] == "forwarded"
    assert result["result"] == "orientation"


def test_metadata_wrapper_returns_zero_without_active_target():
    result = resolve_metadata(
        active_target_data=None,
        target_id=2,
        service_available=True,
        metadata=[1, 2, 3],
    )
    assert result["result"] == [0.0, 0.0, 0.0]


def test_composed_camera_outputs_keep_wrapper_order():
    result = resolve_camera_outputs(
        active_target_data={"type_0x78": 4},
        target_id=2,
        position_type_selector=6,
        orientation_type_selector=6,
        transform_payload="p",
        orientation_payload="o",
        metadata=[1, 2, 3],
        service_available=True,
        position_service_result="p-out",
        orientation_service_result="o-out",
    )
    assert result["source_order"] == [
        "FUN_008140c0",
        "FUN_00814210",
        "FUN_008142c0",
    ]
    assert result["position"]["result"] == "p-out"
    assert result["orientation"]["result"] == "o-out"
    assert result["metadata"]["result"] == [1.0, 2.0, 3.0]
