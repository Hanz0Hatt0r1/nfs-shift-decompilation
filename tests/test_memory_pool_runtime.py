from memory_pool_runtime import (
    CREATE_HELPER,
    RELEASE_HELPER,
    build_memory_pool_contract,
    create_helper_action,
    release_helper_action,
    release_helper_function,
)


def test_contract_preserves_diagnostic_backed_retail_paths():
    contract = build_memory_pool_contract()
    assert contract["format"] == "SHIFT.MemoryPoolRuntime/1"
    assert contract["helpers"] == {
        "create": "FUN_00886900",
        "release": "FUN_00886930",
    }
    assert contract["allocation_path"]["diagnostic_path"] == [
        "FUN_00886900",
        "FUN_00638020",
    ]
    assert contract["allocation_path"]["diagnostic"] == (
        "Unable to allocate %d bytes of memory from the pool (%s)"
    )
    assert contract["free_path"]["diagnostic_path"] == [
        "FUN_00886930",
        "thunk_FUN_0064f3a0",
        "FUN_0064f3a0",
        "FUN_00657c30",
    ]
    assert "Error freeing small alloc" in contract["free_path"]["diagnostic"]


def test_contract_keeps_unproven_abi_and_ownership_explicit():
    contract = build_memory_pool_contract()
    scope = contract["scope"]
    assert scope["pool_allocation_path_proven"] is True
    assert scope["pool_free_path_proven"] is True
    assert scope["allocation_size_argument_role_proven"] is False
    assert scope["released_pointer_argument_role_proven"] is False
    assert scope["allocator_abi_proven"] is False
    assert scope["release_abi_proven"] is False
    assert scope["operator_new_identity_proven"] is False
    assert scope["operator_delete_identity_proven"] is False
    assert scope["object_size_argument_proven"] is False
    assert scope["pool_selector_argument_proven"] is False
    assert scope["release_flag_argument_proven"] is False
    assert scope["ownership_semantics_proven"] is False
    assert "retail_static_evidence" not in contract


def test_contract_promotes_only_diagnostic_backed_physical_roles():
    summary = {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": True,
        "proven_physical_roles": {
            "allocation_size": {
                "proven": True,
                "function": "FUN_00638020",
                "entry_storage": "EDX:4",
            },
            "released_pointer_wrapper": {
                "proven": True,
                "wrapper_input_storage": ["Stack[0x4]:4"],
            },
        },
        "release_byte_behavior": {
            "analysis_complete": True,
            "thunk_forwarded_to_release_backend": True,
            "release_backend_observed": True,
            "controls_conditional_branch": True,
            "bitwise_transformed": False,
        },
        "scope": {
            "release_byte_behavior_observed": True,
            "release_flag_role_proven": False,
            "ownership_semantics_proven": False,
        },
    }

    contract = build_memory_pool_contract(summary)

    assert contract["status"] == "instruction-diagnostic-backed-physical-roles"
    assert contract["scope"]["allocation_size_argument_role_proven"] is True
    assert contract["scope"]["released_pointer_argument_role_proven"] is True
    assert contract["scope"]["object_size_argument_proven"] is False
    assert contract["scope"]["pool_selector_argument_proven"] is False
    assert contract["scope"]["release_flag_argument_proven"] is False
    assert contract["scope"]["allocator_abi_proven"] is False
    assert contract["scope"]["release_abi_proven"] is False
    assert contract["scope"]["ownership_semantics_proven"] is False
    evidence = contract["retail_static_evidence"]
    assert evidence["format"] == "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
    assert evidence["static_evidence_chain_complete"] is True
    assert evidence["allocation_size"] == {
        "proven": True,
        "backend_function": "FUN_00638020",
        "backend_entry_storage": "EDX:4",
    }
    assert evidence["released_pointer"] == {
        "proven": True,
        "wrapper_input_storage": ["Stack[0x4]:4"],
    }
    assert evidence["release_byte_behavior_observed"] is True
    assert evidence["release_byte_behavior"]["controls_conditional_branch"] is True


def test_contract_fails_closed_when_proven_role_lacks_physical_storage():
    summary = {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": False,
        "proven_physical_roles": {
            "allocation_size": {
                "proven": True,
                "function": "FUN_00638020",
                "entry_storage": None,
            },
            "released_pointer_wrapper": {
                "proven": True,
                "wrapper_input_storage": [],
            },
        },
        "release_byte_behavior": {},
        "scope": {},
    }

    contract = build_memory_pool_contract(summary)

    assert contract["status"] == "diagnostic-backed-pool-paths"
    assert contract["scope"]["allocation_size_argument_role_proven"] is False
    assert contract["scope"]["released_pointer_argument_role_proven"] is False
    assert contract["retail_static_evidence"]["allocation_size"]["proven"] is False
    assert contract["retail_static_evidence"]["released_pointer"]["proven"] is False


def test_contract_rejects_wrong_static_summary_format():
    try:
        build_memory_pool_contract({"format": "WRONG"})
    except ValueError as exc:
        assert "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1" in str(exc)
    else:
        raise AssertionError("wrong retail static summary format must fail")


def test_contract_rejects_non_mapping_static_summary():
    try:
        build_memory_pool_contract("bad")  # type: ignore[arg-type]
    except TypeError as exc:
        assert "mapping" in str(exc)
    else:
        raise AssertionError("non-mapping retail static summary must fail")


def test_helper_record_builders_preserve_existing_action_shapes():
    assert create_helper_action(result="storage") == {
        "action": CREATE_HELPER,
        "result": "storage",
    }
    assert release_helper_action(release_old_storage=True) == {
        "action": RELEASE_HELPER,
        "release_old_storage": True,
    }
    assert release_helper_function(source_slot="physics_system+0x3c") == {
        "function": RELEASE_HELPER,
        "source_slot": "physics_system+0x3c",
    }


def test_helper_record_builders_reject_identity_override():
    try:
        release_helper_action(action="FUN_DEADBEEF")
    except ValueError as exc:
        assert "reserved" in str(exc)
    else:
        raise AssertionError("release helper identity override must fail")

    try:
        release_helper_function(function="FUN_DEADBEEF")
    except ValueError as exc:
        assert "reserved" in str(exc)
    else:
        raise AssertionError("release helper function override must fail")
