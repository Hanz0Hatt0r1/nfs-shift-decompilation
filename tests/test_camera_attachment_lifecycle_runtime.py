from camera_attachment_lifecycle_runtime import (
    describe_view_data_destroy_copy,
    describe_view_reset,
    resolve_attachment_result,
)


def test_attachment_resolver_zeroes_result_without_function_or_index():
    result = resolve_attachment_result(
        resolver_present=False,
        attached_index=3,
        resolver_slot="+0x00",
        resolver_arguments=["camera-data", "unused"],
    )
    assert result["status"] == "zero-result"
    assert result["output"] == [0.0, 0.0, 0.0]


def test_attachment_resolver_zeroes_result_for_minus_one_index():
    result = resolve_attachment_result(
        resolver_present=True,
        attached_index=-1,
        resolver_slot="+0x04",
        resolver_arguments=["camera-data", "unused"],
    )
    assert result["status"] == "zero-result"


def test_attachment_resolver_preserves_slot_and_index_when_invoked():
    result = resolve_attachment_result(
        resolver_present=True,
        attached_index=7,
        resolver_slot="+0x04",
        resolver_arguments=["camera-data", "manager-data"],
    )
    assert result["status"] == "resolved"
    assert result["attached_index"] == 7
    assert result["actions"][0]["slot"] == "+0x04"


def test_view_reset_has_exact_lifecycle_order():
    result = describe_view_reset()
    assert [x["action"] for x in result["actions"]] == [
        "write vtable",
        "FUN_0081b350",
        "FUN_00675d70",
        "FUN_0081ac60",
    ]


def test_script_dispatch_uses_param_plus_four_string_source_and_fallback():
    result = describe_view_data_destroy_copy(
        source_words=[0, 1],
        source_bytes=[1, 2, 3, 4],
    )
    assert result["actions"][0]["source"] == "param_1 + 0x04"
    assert result["actions"][0]["fallback"] == "DAT_00aa9b60"
    assert result["actions"][2]["action"] == "FUN_00671100"
