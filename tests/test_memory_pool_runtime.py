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
    scope = build_memory_pool_contract()["scope"]
    assert scope["pool_allocation_path_proven"] is True
    assert scope["pool_free_path_proven"] is True
    assert scope["allocator_abi_proven"] is False
    assert scope["release_abi_proven"] is False
    assert scope["operator_new_identity_proven"] is False
    assert scope["operator_delete_identity_proven"] is False
    assert scope["object_size_argument_proven"] is False
    assert scope["ownership_semantics_proven"] is False


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
