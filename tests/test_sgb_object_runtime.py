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


def test_hierarchy_truncation_blocks_non_strict():
    payload = _hierarchy_payload(count=2)[:36 + 36]
    result = parse_sgb_object_payload(payload, strict=False)
    assert result["decoded"] is False
    assert result["status"] == "blocked"


def test_invalid_bounds_raise():
    with pytest.raises(SGBObjectDecodeError):
        parse_sgb_object_payload(b"\0" * 20)
