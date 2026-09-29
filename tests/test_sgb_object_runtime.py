import struct

import pytest

from sgb_object_runtime import SGBObjectDecodeError, parse_sgb_object_payload


def _object_payload():
    # Common object header is 9 dwords (36 bytes). Extra branch words follow.
    kind_offset, source_offset, aux_offset = 64, 72, 80
    header = struct.pack("<9I", kind_offset, source_offset, aux_offset, 0, 0, 0, 0, 0, 0)
    payload = bytearray(header)
    payload += b"\0" * (64 - len(payload))
    payload += b"OBJECT\0"
    payload += b"SOURCE\0"
    payload += b"AUX\0"
    return bytes(payload)


def _hierarchy_payload(count=2):
    child_bytes = struct.pack("<18I", *range(18))
    kind_offset = 36 + len(child_bytes)
    source_offset = kind_offset + 12
    aux_offset = source_offset + 4
    header = struct.pack("<9I", kind_offset, source_offset, aux_offset, 0, 0, 0, 0, 0, 0)
    raw = bytearray(header)
    raw[34] = count
    raw[35] = 2
    raw += child_bytes
    raw += b"HIERARCHY\0"
    raw += b"SRC\0"
    raw += b"AUX\0"
    return bytes(raw)


def test_object_kind_dispatch_is_reconstructed():
    result = parse_sgb_object_payload(_object_payload())
    assert result["kind"]["text"] == "OBJECT"
    assert result["decoded"] is True


def test_hierarchy_child_record_size_is_36_bytes():
    result = parse_sgb_object_payload(_hierarchy_payload())
    assert result["kind"]["text"] == "HIERARCHY"
    assert result["hierarchy_count"] == 2
    assert result["child_table_size"] == 72
    assert result["children"][0]["runtime_copy_order"] == [6, 3, 4, 5, 1, 2, 0, 7, 8]


def test_hierarchy_child_runtime_layout_is_proven():
    result = parse_sgb_object_payload(_hierarchy_payload())
    child = result["children"][0]
    assert child["record_bytes"] == 36
    assert child["runtime_element_bytes"] == 0x28
    assert child["runtime_destination_word_offsets"] == {
        "0x00": 6,
        "0x04": 3,
        "0x08": 4,
        "0x0c": 5,
        "0x10": 0,
        "0x14": 1,
        "0x18": 2,
        "0x1c": 7,
        "0x20": 8,
    }
    assert child["runtime_source_word_offsets"] == {
        "0": 0x10,
        "1": 0x14,
        "2": 0x18,
        "3": 0x04,
        "4": 0x08,
        "5": 0x0c,
        "6": 0x00,
        "7": 0x1c,
        "8": 0x20,
    }


def test_hierarchy_truncation_blocks_non_strict():
    payload = bytearray(_hierarchy_payload(count=2))
    # Keep the proven dispatcher string inside the bounded payload while the
    # 72-byte child table is deliberately truncated after one record.
    struct.pack_into("<I", payload, 0, 40)
    payload[40:50] = b"HIERARCHY\0"
    result = parse_sgb_object_payload(bytes(payload[:72]), strict=False)
    assert result["decoded"] is False
    assert result["status"] == "blocked"
    assert result["blockers"]


def test_invalid_bounds_raise():
    with pytest.raises(SGBObjectDecodeError):
        parse_sgb_object_payload(b"\0" * 20)
