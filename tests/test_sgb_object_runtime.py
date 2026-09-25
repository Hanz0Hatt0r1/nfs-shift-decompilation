import struct

import pytest

from sgb_object_runtime import SGBObjectDecodeError, parse_sgb_object_payload


def _header(kind_offset=40, source_offset=48, aux_offset=56, count=0):
    words = [kind_offset, source_offset, aux_offset, 0, 0, 0, 0, 0, 0, 0]
    raw = struct.pack("<10I", *words)
    # byte 34 is hierarchy count; byte 35 is hierarchy type.
    buf = bytearray(raw)
    buf[34] = count
    buf[35] = 2
    return bytes(buf)


def test_object_kind_dispatch_is_reconstructed():
    payload = bytearray(_header())
    payload += b"\0\0\0\0"
    payload += b"OBJECT\0"
    payload += b"SOURCE\0"
    payload += b"AUX\0"
    result = parse_sgb_object_payload(bytes(payload))
    assert result["kind"]["text"] == "OBJECT"
    assert result["decoded"] is True


def test_hierarchy_child_record_size_is_36_bytes():
    payload = bytearray(_header(count=2))
    payload += b"\0\0\0\0"
    payload += b"HIERARCHY\0"
    payload += b"SRC\0"
    payload += b"AUX\0"
    payload += struct.pack("<18I", *range(18))
    result = parse_sgb_object_payload(bytes(payload))
    assert result["kind"]["text"] == "HIERARCHY"
    assert result["hierarchy_count"] == 2
    assert result["child_table_size"] == 72
    assert result["children"][0]["runtime_copy_order"] == [6, 3, 4, 5, 1, 2, 0, 7, 8]


def test_hierarchy_truncation_blocks_non_strict():
    payload = bytearray(_header(count=2))
    payload += b"\0\0\0\0"
    payload += b"HIERARCHY\0SRC\0AUX\0"
    payload += struct.pack("<9I", *range(9))
    result = parse_sgb_object_payload(bytes(payload), strict=False)
    assert result["decoded"] is False
    assert result["status"] == "blocked"


def test_invalid_bounds_raise():
    with pytest.raises(SGBObjectDecodeError):
        parse_sgb_object_payload(b"\0" * 20)
