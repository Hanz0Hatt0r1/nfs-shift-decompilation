import pytest

from camera_dynamic_array_runtime import (
    grow_dword11_array,
    grow_uint16_array,
    next_dword11_element_address,
    next_uint16_element_address,
)


def _static_release_summary(*, proven: bool = True):
    return {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": True,
        "proven_physical_roles": {
            "released_pointer_wrapper": {
                "proven": proven,
                "wrapper_input_storage": ["Stack[0x4]:4"] if proven else [],
            }
        },
        "release_byte_behavior": {},
        "scope": {},
    }


def _source_release_summary(
    *,
    index: int = 0,
    callers=None,
    consistent: bool = True,
):
    if callers is None:
        callers = ["FUN_00813080", "FUN_008166b0"]
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
                    "source_argument_indices": [index],
                    "source_argument_index_consistent": consistent,
                    "source_argument_index": index if consistent else None,
                    "observed_source_expressions": ["old_storage"],
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


def test_uint16_growth_preserves_elementwise_copy_mode():
    result = grow_uint16_array(
        element_stride=2,
        old_count=3,
        old_capacity=3,
        source_storage=[1, 2, 3],
        copy_memcpy_mode=False,
        new_capacity=6,
    )
    assert result["copy_method"] == "elementwise_uint16"
    assert result["copied_elements"] == [1, 2, 3]
    assert result["actions"][-1] == {
        "action": "FUN_00886930",
        "release_old_storage": True,
    }
    assert "memory_wrapper_evidence" not in result


def test_uint16_growth_preserves_memcpy_mode():
    result = grow_uint16_array(
        element_stride=2,
        old_count=2,
        old_capacity=2,
        source_storage=[10, 11],
        copy_memcpy_mode=True,
        new_capacity=4,
    )
    assert result["copy_method"] == "memcpy_s"


def test_uint16_next_address_is_stride_times_index_plus_base():
    result = next_uint16_element_address(
        element_stride=2,
        current_index=4,
        base_offset=0x20,
    )
    assert result["address_offset"] == 0x28


def test_dword11_growth_requires_exactly_eleven_dwords_per_element():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[0] * 11],
        copy_memcpy_mode=False,
        new_capacity=2,
    )
    assert result["copy_method"] == "elementwise_11_dword"
    assert result["copied_elements"] == [[0] * 11]
    assert result["actions"][-1]["action"] == "FUN_00886930"


def test_dword11_growth_preserves_memcpy_mode():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[1] * 11],
        copy_memcpy_mode=True,
        new_capacity=2,
    )
    assert result["copy_method"] == "memcpy_s"


def test_dword11_next_address_uses_same_formula():
    result = next_dword11_element_address(
        element_stride=0x2c,
        current_index=3,
        base_offset=0x10,
    )
    assert result["address_offset"] == 0x94


def test_uint16_growth_crosschecks_released_pointer_role_for_exact_caller():
    result = grow_uint16_array(
        element_stride=2,
        old_count=2,
        old_capacity=2,
        source_storage=[10, 11],
        copy_memcpy_mode=True,
        new_capacity=4,
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["format"] == "SHIFT.CameraDynamicArrayMemoryCrosscheck/1"
    assert evidence["helper"] == "FUN_00886930"
    assert evidence["role"] == "released-pointer"
    assert evidence["caller"] == "FUN_00813080"
    assert evidence["expected_source_argument_index"] == 0
    assert evidence["observed_source_argument_index"] == 0
    assert evidence["physical_role_proven"] is True
    assert evidence["source_role_proven"] is True
    assert evidence["caller_observed"] is True
    assert evidence["ready"] is True
    assert evidence["blockers"] == []
    assert evidence["scope"]["release_abi_proven"] is False
    assert evidence["scope"]["release_flag_role_proven"] is False
    assert evidence["scope"]["ownership_semantics_proven"] is False
    assert result["actions"][-1] == {
        "action": "FUN_00886930",
        "release_old_storage": True,
    }


def test_dword11_growth_crosschecks_its_own_release_callsite():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[1] * 11],
        copy_memcpy_mode=True,
        new_capacity=2,
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["caller"] == "FUN_008166b0"
    assert evidence["caller_observed"] is True
    assert evidence["ready"] is True


def test_release_pointer_crosscheck_fails_closed_without_static_role():
    result = grow_uint16_array(
        element_stride=2,
        old_count=1,
        old_capacity=1,
        source_storage=[7],
        copy_memcpy_mode=False,
        new_capacity=2,
        retail_source_semantic_summary=_source_release_summary(),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["ready"] is False
    assert "released_pointer_physical_role_not_proven" in evidence["blockers"]
    assert "released_pointer_source_role_not_proven" in evidence["blockers"]


def test_release_pointer_crosscheck_rejects_wrong_source_index():
    result = grow_uint16_array(
        element_stride=2,
        old_count=1,
        old_capacity=1,
        source_storage=[7],
        copy_memcpy_mode=False,
        new_capacity=2,
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(index=1),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["source_role_proven"] is True
    assert evidence["observed_source_argument_index"] == 1
    assert evidence["ready"] is False
    assert evidence["blockers"] == ["released_pointer_source_index_mismatch"]


def test_release_pointer_crosscheck_requires_exact_growth_caller():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[1] * 11],
        copy_memcpy_mode=False,
        new_capacity=2,
        retail_static_summary=_static_release_summary(),
        retail_source_semantic_summary=_source_release_summary(callers=["FUN_00813080"]),
    )

    evidence = result["memory_wrapper_evidence"]
    assert evidence["ready"] is False
    assert evidence["caller_observed"] is False
    assert evidence["blockers"] == ["release_caller_not_observed"]


def test_release_pointer_crosscheck_rejects_wrong_summary_format():
    with pytest.raises(ValueError, match="SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"):
        grow_uint16_array(
            element_stride=2,
            old_count=1,
            old_capacity=1,
            source_storage=[7],
            copy_memcpy_mode=False,
            new_capacity=2,
            retail_static_summary={"format": "WRONG"},
        )
