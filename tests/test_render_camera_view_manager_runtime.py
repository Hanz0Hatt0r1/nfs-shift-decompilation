from render_camera_view_manager_runtime import (
    describe_camera_manager_refresh_bridge,
    describe_render_camera_view_manager_constructor,
    describe_render_camera_view_manager_delete,
    describe_render_camera_view_manager_reset,
    get_render_camera_view_manager_singleton,
)


def _static_release_summary():
    return {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": True,
        "proven_physical_roles": {
            "released_pointer_wrapper": {
                "proven": True,
                "wrapper_input_storage": ["Stack[0x4]:4"],
            }
        },
        "release_byte_behavior": {},
        "scope": {},
    }


def _source_release_summary(*, callers=None):
    if callers is None:
        callers = ["FUN_008112b0", "FUN_0081b140"]
    return {
        "format": "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1",
        "allocation_size_role_proven": False,
        "released_pointer_role_proven": True,
        "semantic_profiles_consistent": True,
        "wrapper_profiles": [
            {
                "wrapper": "FUN_00886930",
                "allocation_size": None,
                "released_pointer": {
                    "proven_callsite_count": len(callers),
                    "source_argument_indices": [0],
                    "source_argument_index_consistent": True,
                    "source_argument_index": 0,
                    "observed_source_expressions": ["this"],
                    "caller_count": len(callers),
                    "callers": list(callers),
                },
                "proven_source_roles": ["released-pointer"],
                "unresolved_source_roles": [
                    "pool-selector",
                    "alignment",
                    "release-flag",
                    "delete-kind",
                    "ownership",
                ],
                "blockers": [],
            }
        ],
        "release_byte_behavior": {},
        "scope": {
            "release_flag_role_proven": False,
            "ownership_semantics_proven": False,
        },
    }


def test_constructor_sets_exact_vtable_and_runtime_label():
    result = describe_render_camera_view_manager_constructor()
    assert result["actions"][1]["value"] == "PTR_FUN_00b15aa8"
    assert result["actions"][2]["argument"] == "RenderCameraViewManager"


def test_reset_delegates_to_00647b20():
    result = describe_render_camera_view_manager_reset()
    assert result["actions"][1]["action"] == "FUN_00647b20"


def test_delete_only_frees_when_low_bit_is_set():
    result = describe_render_camera_view_manager_delete(delete_flag=0)
    assert result["actions"][1] == {
        "action": "FUN_00886930",
        "condition": "(delete_flag & 1) != 0",
    }
    assert "memory_wrapper_evidence" not in result
    result = describe_render_camera_view_manager_delete(delete_flag=1)
    assert result["delete_flag"] == 1


def test_delete_crosschecks_released_pointer_for_exact_wrapper_caller():
    result = describe_render_camera_view_manager_delete(
        delete_flag=1,
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["format"] == "SHIFT.CameraDeletingWrapperMemoryCrosscheck/1"
    assert evidence["helper"] == "FUN_00886930"
    assert evidence["role"] == "released-pointer"
    assert evidence["caller"] == "FUN_008112b0"
    assert evidence["observed_source_argument_index"] == 0
    assert evidence["caller_observed"] is True
    assert evidence["ready"] is True
    assert evidence["blockers"] == []
    assert evidence["scope"]["release_abi_proven"] is False
    assert evidence["scope"]["release_flag_role_proven"] is False
    assert evidence["scope"]["delete_kind_role_proven"] is False
    assert evidence["scope"]["ownership_semantics_proven"] is False
    assert result["actions"][1]["condition"] == "(delete_flag & 1) != 0"


def test_singleton_initializes_once_and_registers_atexit():
    result = get_render_camera_view_manager_singleton(guard_before=0)
    assert result["status"] == "initialized"
    assert result["guard_after"] == 1
    assert result["actions"][2]["action"] == "_atexit"


def test_singleton_returns_existing_without_reconstruction():
    result = get_render_camera_view_manager_singleton(guard_before=1)
    assert result["status"] == "existing"
    assert result["actions"] == []


def test_refresh_bridge_calls_camera_manager_refresh_and_returns_zero():
    result = describe_camera_manager_refresh_bridge()
    assert [a["action"] for a in result["actions"]] == [
        "FUN_0080bfb0",
        "FUN_0080c180",
    ]
    assert result["return_value"] == 0
