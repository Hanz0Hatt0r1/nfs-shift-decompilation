#!/usr/bin/env python3
"""Check the captured pre-wait shader payloads and export-register decoding."""

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_shader_export_audit_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-wait-shader-export-audit.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["capture"]["wait"]["outer_byte_offset"] == "0x49C"
assert evidence["capture"]["wait"]["guest_physical_word"] == "0x1B964004"
assert evidence["translator_identity"]["source_commit"].startswith("6277bda6")

export_address = evidence["capture"]["shader_register_definition"]["eA_register_index"]
export_data = set(evidence["capture"]["shader_register_definition"]["eM_register_indices"])
loads = evidence["capture"]["shader_loads_before_wait"]
assert len(loads) == 4
for shader in loads:
    words = shader["code_dwords_be"]
    assert len(words) == shader["dword_count"]
    raw = b"".join(struct.pack(">I", int(word, 16)) for word in words)
    assert hashlib.sha256(raw).hexdigest() == shader["code_sha256"]
    assert shader["translated_by_captured_glsl_path"] is True
    assert shader["generated_storage_buffer"] is False
    assert shader["generated_image_store"] is False
    assert shader["generated_atomic_store"] is False
    scheduled = set(shader["scheduled_alu_instruction_addresses"])
    assert all(0 <= instruction < len(words) // 3 for instruction in scheduled)
    assert all(item["instruction"] in scheduled for item in shader["export_destinations"])
    captured_exports = []
    for instruction in sorted(scheduled):
        word0 = int(words[instruction * 3], 16)
        if not (word0 & 0x8000):
            continue
        destination = word0 & 0x3F
        assert destination != export_address
        assert destination not in export_data
        captured_exports.append((instruction, destination))
    assert captured_exports == [
        (item["instruction"], item["register_index"])
        for item in shader["export_destinations"]
    ]

draws = evidence["capture"]["nested_draws"]
assert draws["packet_count"] == 24
assert draws["raw_packet_words"] == ["c0003600", "00010081"]
assert evidence["capture"]["register_writes_before_wait"]["color_info"] == "0x00010000"
assert evidence["capture"]["register_writes_before_wait"]["copy_dest_base_0x2319"] == "0x00000000"
assert "Preserve WAIT_REG_MEM" in evidence["interpretation"]["next_step"]

print("retail pre-wait shader evidence verifies no explicit eA/eM export to the polled word")
