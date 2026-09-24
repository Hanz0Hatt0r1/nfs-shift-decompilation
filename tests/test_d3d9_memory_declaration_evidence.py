import struct

import pytest

from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration


def _declaration_bytes():
    return b"".join(
        (
            struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
            struct.pack("<HHBBBB", 0, 12, 4, 0, 6, 1),
            struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        )
    )


def test_runtime_memory_capture_records_address_range_and_hashes():
    dump = b"\xAA\xBB" + _declaration_bytes() + b"\xCC\xDD"
    result = capture_d3d9_memory_declaration(
        dump,
        base_address=0x12340000,
        offset=2,
        length=len(_declaration_bytes()),
        source_name="capture.bin",
    )

    assert result["format"] == "SHIFT.D3D9MemoryDeclarationEvidence/1"
    assert result["status"] == "match"
    assert result["endianness"] == "little"
    assert result["memory"]["dump_base_address"] == "0x0000000012340000"
    assert result["memory"]["slice_start_address"] == "0x0000000012340002"
    assert result["memory"]["slice_length"] == 24
    assert result["provenance"]["source_name"] == "capture.bin"
    assert len(result["provenance"]["source_sha256"]) == 64
    assert len(result["provenance"]["slice_sha256"]) == 64
    assert result["extraction"]["complete_array"] is True
    assert result["extraction"]["end_sentinel_index"] == 2
    assert result["extraction"]["declaration_array_records"] == 3
    assert result["extraction"]["post_sentinel_bytes"] == 0
    assert result["declaration_instance"]["status"] == "match"
    assert result["evidence_boundary"]["runtime_memory_dump"] == "supplied"
    assert result["evidence_boundary"]["runtime_declaration_array"] == "observed"
    assert result["evidence_boundary"]["source_authenticity"] == "not-authenticated"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_runtime_memory_capture_trims_to_end_sentinel_and_preserves_extra_bytes():
    payload = _declaration_bytes() + b"\x11" * 16
    result = capture_d3d9_memory_declaration(payload, base_address=0x5000)

    assert result["status"] == "match"
    assert result["extraction"]["declaration_array_bytes"] == 24
    assert result["extraction"]["post_sentinel_bytes"] == 16
    assert result["declaration_instance"]["payload"]["decoded_records"] == 3
    assert result["bytes"]["length"] == 40


def test_runtime_memory_capture_without_end_sentinel_is_partial():
    payload = struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0)
    result = capture_d3d9_memory_declaration(payload, base_address=0x9000)

    assert result["status"] == "partial"
    assert result["extraction"]["complete_array"] is False
    assert result["extraction"]["end_sentinel_status"] == "not-present"
    assert result["evidence_boundary"]["runtime_declaration_array"] == "partial"


def test_runtime_memory_capture_rejects_out_of_range_slice():
    with pytest.raises(ValueError):
        capture_d3d9_memory_declaration(
            b"\x00" * 16,
            base_address=0x1000,
            offset=12,
            length=8,
        )


def test_runtime_memory_capture_rejects_address_overflow():
    with pytest.raises(ValueError):
        capture_d3d9_memory_declaration(
            b"\x00" * 8,
            base_address=0xFFFFFFFFFFFFFFFF,
        )
