from derived_camera_view_runtime import (
    describe_derived_camera_view_constructor,
    describe_derived_camera_view_delete,
    describe_derived_camera_view_reset,
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
        callers = ["FUN_0081b140"]
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


def test_derived_constructor_preserves_exact_projection_overrides():
    result = describe_derived_camera_view_constructor()
    assert result["writes"]["+0x34"] == 0x3F860A92
    assert result["writes"]["+0x48"] == 0x3F000000
    assert result["writes"]["+0x4c"] == 0
    assert result["writes"]["+0x50"] == 0
    assert result["writes"]["+0x5c"] == 0


def test_derived_constructor_sets_final_vtable():
    result = describe_derived_camera_view_constructor()
    assert result["actions"][5]["value"] == "PTR_FUN_00b162e8"


def test_derived_reset_delegates_to_base_reset():
    result = describe_derived_camera_view_reset()
    assert result["actions"][1]["action"] == "FUN_0081ac60"


def test_derived_delete_calls_cleanup_only_when_flag_is_set():
    result = describe_derived_camera_view_delete()
    assert result["actions"][1] == {
        "action": "FUN_00886930",
        "condition": "param_1 & 1",
    }
    assert "memory_wrapper_evidence" not in result


def test_derived_delete_crosschecks_released_pointer_for_exact_caller():
    result = describe_derived_camera_view_delete(
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["format"] == "SHIFT.CameraDeletingWrapperMemoryCrosscheck/1"
    assert evidence["caller"] == "FUN_0081b140"
    assert evidence["observed_source_argument_index"] == 0
    assert evidence["caller_observed"] is True
    assert evidence["ready"] is True
    assert evidence["blockers"] == []
    assert evidence["scope"]["release_flag_role_proven"] is False
    assert evidence["scope"]["delete_kind_role_proven"] is False
    assert evidence["scope"]["ownership_semantics_proven"] is False
    assert result["actions"][1]["condition"] == "param_1 & 1"


def test_derived_delete_fails_closed_when_source_summary_lacks_caller():
    result = describe_derived_camera_view_delete(
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(
            callers=["FUN_008112b0"]
        ),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["caller_observed"] is False
    assert evidence["ready"] is False
    assert evidence["blockers"] == ["release_caller_not_observed"]
