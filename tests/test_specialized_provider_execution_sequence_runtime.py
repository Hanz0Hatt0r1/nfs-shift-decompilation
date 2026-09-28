import specialized_provider_execution_sequence_runtime as runtime


def test_execution_sequence_has_nine_steps():
    result = runtime.build_execution_sequence()

    assert len(result["steps"]) == 9
    assert [step["index"] for step in result["steps"]] == list(range(9))


def test_provider_cleanup_precedes_common_preparation():
    steps = runtime.build_execution_sequence()["steps"]

    assert steps[0]["stage"] == "backend-branch"
    assert steps[0]["provider_action"] == (
        "call provider vtable +0x20 cleanup"
    )
    assert steps[1]["function"] == "FUN_007b3ed0"
    assert steps[2]["function"] == "FUN_007bb8d0"


def test_body_and_constraint_strides_are_exact():
    domains = runtime.build_execution_sequence()["loop_domains"]

    assert domains["BODY"] == {
        "count_field": "+0x10",
        "stride": "0x170",
    }
    assert domains["JOINT/HINGE"] == {
        "count_field": "+0x18",
        "stride": "0xa0",
    }
    assert domains["BAR"] == {
        "count_field": "+0x28",
        "stride": "0xb8",
    }


def test_final_dispatch_preserves_provider_and_builtin_paths():
    final = runtime.build_execution_sequence()["steps"][-1]

    assert final["condition"] == "physics_system+0x48 != 0"
    assert final["provider_action"] == (
        "call provider vtable +0x18 solve"
    )
    assert final["builtin_action"].startswith(
        "otherwise call FUN_007b0f20"
    )


def test_validate_execution_sequence_is_ready():
    result = runtime.validate_execution_sequence()

    assert result["ready"] is True
    assert result["errors"] == []


def test_contract_marks_accumulation_semantics_as_structural_only():
    result = runtime.build_execution_sequence_contract()

    assert result["status"] == "source-backed-provider-execution-sequence"
    assert "scalar coefficient semantics" in " ".join(
        result["limitations"]
    )
