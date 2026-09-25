from tracking_target_resolution_runtime import (
    describe_tracking_target_forward,
    query_tracking_target_position,
    resolve_tracking_target,
)


def test_specialized_target_requires_both_global_flags_clear_and_rtti():
    result = resolve_tracking_target(
        manager_has_target=True,
        manager_target="manager-target",
        global_service_flag_82e=False,
        global_service_flag_82f=False,
        nested_target="special-target",
        nested_target_has_rtti=True,
    )
    assert result["status"] == "specialized-global-target"
    assert result["target"] == "special-target"


def test_target_resolver_falls_back_when_any_specialized_predicate_fails():
    result = resolve_tracking_target(
        manager_has_target=True,
        manager_target="manager-target",
        global_service_flag_82e=True,
        global_service_flag_82f=False,
        nested_target="special-target",
        nested_target_has_rtti=True,
    )
    assert result["target"] == "manager-target"


def test_target_position_zeroes_when_target_state_is_negative():
    result = query_tracking_target_position(
        resolved_target="target",
        target_state=-1,
    )
    assert result["output"] == [0.0, 0.0, 0.0]


def test_target_position_forwards_to_155f0_when_state_is_valid():
    result = query_tracking_target_position(
        resolved_target="target",
        target_state=0,
    )
    assert result["status"] == "query-helper"
    assert result["actions"][0]["action"] == "FUN_008155f0"


def test_target_forward_uses_rtti_pointer_or_null():
    result = describe_tracking_target_forward(
        source_object="obj",
        rtti_result="typed-target",
    )
    assert result["forwarded"] == "typed-target"
    null = describe_tracking_target_forward(source_object=None, rtti_result=None)
    assert null["status"] == "null-forwarded"
    assert null["actions"][1]["argument"] is None
