from trackside_score_endpoints_runtime import (
    build_forward_endpoint_record,
    copy_static_camera_payload,
    describe_camera_script_event,
    endpoint_readiness,
    resolve_shake_target_metadata,
    select_trackside_score,
    static_camera_property_registration,
)


def test_trackside_score_returns_smallest_candidate():
    result = select_trackside_score(candidate_scores=[4.0, 2.0, 3.0])
    assert result["status"] == "complete"
    assert result["score"] == 2.0
    assert result["selected"] == 1


def test_trackside_score_stops_immediately_on_negative_score():
    result = select_trackside_score(candidate_scores=[5.0, -0.5, -10.0])
    assert result["status"] == "negative-early-exit"
    assert result["score"] == -0.5
    assert len(result["trace"]) == 2


def test_trackside_score_empty_returns_float_max_and_minus_one():
    result = select_trackside_score(candidate_scores=[])
    assert result["score"] == 3.4028235e38
    assert result["selected"] == -1


def test_script_event_dispatches_only_when_event_resolves():
    result = describe_camera_script_event(
        event_name="OnEnd",
        resolved_event="event",
        source_event="source",
    )
    assert result["status"] == "dispatched"
    assert result["actions"][-1]["action"] == "FUN_00671100"


def test_shake_target_metadata_prefers_attached_target():
    result = resolve_shake_target_metadata(
        active_target_data="target",
        attached_target_id=4,
        fallback_metadata=[9, 9, 9],
        direct_metadata=[1, 2, 3],
    )
    assert result["status"] == "attached-target"
    assert result["result"] == [1.0, 2.0, 3.0]


def test_shake_target_metadata_falls_back_to_camera_manager():
    result = resolve_shake_target_metadata(
        active_target_data=None,
        attached_target_id=-1,
        fallback_metadata=[9, 8, 7],
        direct_metadata=None,
    )
    assert result["status"] == "camera-manager-fallback"
    assert result["result"] == [9.0, 8.0, 7.0]


def test_static_camera_copy_preserves_scalar_and_byte_groups():
    source = {offset: offset for offset in [
        0x00, 0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
        0x20, 0x21, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38,
    ]}
    result = copy_static_camera_payload(source)
    assert result["scalar_copy"]["+0x34"] == 0x34
    assert result["byte_copy"]["+0x21"] == 0x21
    assert result["nested_blocks"][0]["helper"] == "FUN_00814340"


def test_static_camera_registration_retains_duplicate_offsets():
    result = static_camera_property_registration()
    screen_velocity = [
        p for p in result["properties"] if p["name"] == "ShakeScreenVelocity"
    ][0]
    shake_frequency = [
        p for p in result["properties"] if p["name"] == "ShakeFrequency"
    ][0]
    assert screen_velocity["offset"] == 0xb8
    assert shake_frequency["offset"] == 0xb8


def test_endpoint_readiness_is_or_of_the_two_spline_gates():
    assert endpoint_readiness(start_gate=1, end_gate=0)["result"] == 1
    assert endpoint_readiness(start_gate=0, end_gate=1)["result"] == 1
    assert endpoint_readiness(start_gate=0, end_gate=0)["result"] == 0


def test_forward_endpoint_record_uses_default_scalar_20_when_record_is_zero():
    result = build_forward_endpoint_record(
        record_position=[1, 2, 3],
        record_scalar_1c=0.5,
        record_scalar_20=0.0,
        current_index=4,
        default_scalar_20=7.0,
    )
    assert result["output"]["+0x00"] == 1.0
    assert result["output"]["+0x04"] == 2.0
    assert result["output"]["+0x08"] == 3.0
    assert result["output"]["+0x10"] == 2
    assert result["output"]["+0x14"] == 4
    assert result["output"]["+0x20"] == 7.0
