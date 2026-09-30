import struct

from sgb_object_runtime import (
    DAMAGE_RUNTIME_PAIR,
    parse_sgb_object_payload,
)


def _damage_payload() -> bytes:
    # No retail DAMAGE sample is claimed here. This fixture covers only the
    # common 0x24-byte object header that Phase 543 already proved.
    buf = bytearray(b"\0" * 0x24)

    def add(text: str) -> int:
        offset = len(buf)
        buf.extend(text.encode("utf-8") + b"\0")
        return offset

    kind = add("DAMAGE")
    source = add("DAMAGE_SOURCE")
    third = add("DAMAGE_AUX")
    struct.pack_into("<III", buf, 0, kind, source, third)
    struct.pack_into("<I", buf, 0x0C, 1)
    struct.pack_into("<4f", buf, 0x10, 0.0, 0.0, 0.0, 1.0)
    struct.pack_into("<bBBB", buf, 0x20, 3, 0, 2, 2)
    return bytes(buf)


def test_damage_wrapper_exposes_two_child_runtime_pair():
    report = parse_sgb_object_payload(_damage_payload())
    wrapper = report["runtime_wrapper"]
    pair = wrapper["runtime_pair_contract"]

    assert report["kind"]["text"] == "DAMAGE"
    assert report["decoded"] is True
    assert wrapper["constructor"] == "FUN_00698b00"
    assert wrapper["destructor"] == "FUN_0068cf40"
    assert wrapper["vtable"] == 0x00AF7C88
    assert wrapper["allocation_bytes"] == 0xA0
    assert wrapper["proven_fields"] == {
        "matrix_count": 0x80,
        "runtime_matrix_array": 0x84,
        "runtime_subobject_pair": 0x88,
        "matrix_number": 0x90,
    }
    assert pair["subobject_pair"]["array_offset"] == 0x88
    assert pair["subobject_pair"]["pointer_count_consumed_by_runtime"] == 2
    assert pair["subobject_pair"]["destructor_loop_bytes"] == 8
    assert pair["matrix"]["count_offset"] == 0x80
    assert pair["matrix"]["array_offset"] == 0x84
    assert pair["matrix"]["element_bytes"] == 0x28
    assert pair["matrix_number_offset"] == 0x90


def test_damage_proxy_methods_forward_symmetrically_to_both_children():
    proxy = DAMAGE_RUNTIME_PAIR["proxy_vfuncs"]

    assert proxy["0x10"] == {
        "function": "FUN_0068c6d0",
        "child_vfunc_offset": 0x10,
        "aggregation": "forward-to-both",
    }
    assert proxy["0x14"]["function"] == "FUN_0068c750"
    assert proxy["0x14"]["child_vfunc_offset"] == 0x14
    assert proxy["0x18"]["function"] == "FUN_0068c710"
    assert proxy["0x18"]["child_vfunc_offset"] == 0x18
    assert proxy["0x20"] == {
        "function": "FUN_0068c790",
        "child_vfunc_offset": 0x20,
        "aggregation": "logical-and",
    }
    assert proxy["0x28"] == {
        "function": "FUN_0068c7c0",
        "child_vfunc_offset": 0x28,
        "aggregation": "logical-and",
    }


def test_damage_specialized_vfunc_checks_both_children():
    special = DAMAGE_RUNTIME_PAIR["proxy_vfuncs"]["0x24"]
    assert special["function"] == "FUN_0068dea0"
    assert special["child_probe_vfunc_offset"] == 0x3C
    assert special["fallback_child_vfunc_offset"] == 0x24
    assert special["aggregation"] == "specialized-two-child-selection"


def test_damage_destructor_ownership_is_bounded_to_pair():
    pair = DAMAGE_RUNTIME_PAIR
    assert pair["destructor"] == "FUN_0068cf40"
    assert pair["ownership"]["matrix_array_free_base_adjust"] == -8
    assert pair["ownership"]["subobject_pair_array_freed"] is True
    assert pair["ownership"]["subobject_pair_array_cleared"] is True
    assert pair["subobject_pair"]["destructor_child_release_vfunc_offset"] == 0


def test_damage_runtime_consumer_uses_matrix_number_and_pair_outputs():
    construction = DAMAGE_RUNTIME_PAIR["construction"]
    assert construction["matrix_stack_builder"] == "FUN_0068cfe0"
    assert construction["matrix_number_index_stride"] == 0x40
    assert construction["child_output_vfunc_offset"] == 0x24
    assert construction["child_output_fields"] == [0xA0, 0xA4]


def test_damage_serialized_child_layout_remains_explicitly_partial():
    report = parse_sgb_object_payload(_damage_payload())
    serialized = report["damage_serialized_layout"]

    assert serialized["status"] == "partial"
    assert serialized["matrix_count_offset"] == 0x22
    assert serialized["subobject_count_offset"] == 0x23
    assert serialized["runtime_matrix_loader"] == "FUN_00699870"
    assert serialized["runtime_subobject_pair_offset"] == 0x88
    assert serialized["runtime_pair_pointer_count"] == 2
    assert serialized["binary_subobject_offset_table"] == "not-normalized"
    assert DAMAGE_RUNTIME_PAIR["serialized_layout_status"] == "partial"
