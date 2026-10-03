import hashlib
import importlib.util
import struct
from pathlib import Path

import pytest


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _contract_module():
    return _load(
        Path(__file__).resolve().parents[1]
        / "src"
        / "physics"
        / "body_frame_integration_static.py"
    )


def _verifier_module():
    return _load(
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "verify_body_frame_integration_binary.py"
    )


def _synthetic_pe(payload: bytes, *, start_va: int = 0x00401020) -> bytes:
    data = bytearray(0x500)
    data[:2] = b"MZ"
    pe = 0x80
    struct.pack_into("<I", data, 0x3C, pe)
    data[pe : pe + 4] = b"PE\0\0"
    struct.pack_into("<H", data, pe + 4, 0x014C)
    struct.pack_into("<H", data, pe + 6, 1)
    struct.pack_into("<H", data, pe + 20, 0xE0)
    optional = pe + 24
    struct.pack_into("<H", data, optional, 0x10B)
    struct.pack_into("<I", data, optional + 28, 0x00400000)
    section = optional + 0xE0
    data[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<I", data, section + 8, 0x200)
    struct.pack_into("<I", data, section + 12, 0x1000)
    struct.pack_into("<I", data, section + 16, 0x200)
    struct.pack_into("<I", data, section + 20, 0x200)
    offset = 0x200 + (start_va - 0x00401000)
    data[offset : offset + len(payload)] = payload
    return bytes(data)


def test_contract_closes_persistent_body_writer_gap_without_renaming():
    module = _contract_module()
    contract = module.build_contract()
    module.validate_contract(contract)

    assert contract["closed_boundaries"] == {
        "accumulator_b_to_motion_triplet": True,
        "motion_triplet_to_origin": True,
        "cross_vector_to_basis": True,
        "accumulator_a_to_prepared_vector": True,
        "prepared_vector_to_cross_vector": True,
        "body_array_stride_and_count": True,
        "two_half_step_order_inside_FUN_00770e80": True,
    }
    integrator = contract["functions"]["FUN_007bab70"]
    equations = {row["lane"]: row["equation"] for row in integrator["writes"]}
    assert equations["origin"] == "origin += motion_triplet * dt"
    assert equations["motion_triplet"] == (
        "motion_triplet += accumulator_b * scalar_0x90 * dt"
    )
    assert equations["prepared_vector"] == "prepared_vector += accumulator_a * dt"
    assert equations["cross_vector"] == "cross_vector = symmetric_tensor * prepared_vector"
    assert all(row["promoted_name"] is False for row in contract["functions"].values())
    assert contract["scope"]["linux_runtime_implementation_changed"] is False


def test_binary_verifier_maps_file_backed_virtual_address_and_hashes_exact_bytes():
    module = _verifier_module()
    payload = bytes.fromhex("558bec90c3")
    start = 0x00401020
    pe = _synthetic_pe(payload, start_va=start)
    report = module.verify_function_hashes(
        pe,
        {
            "FUN_test": {
                "start": start,
                "end": start + len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        },
    )
    assert report["verified"] is True
    assert report["functions"][0]["byte_count"] == len(payload)
    assert report["functions"][0]["status"] == "exact-retail-function-bytes-verified"


def test_binary_verifier_fails_closed_on_function_byte_mismatch():
    module = _verifier_module()
    payload = b"\x90\xc3"
    start = 0x00401020
    pe = _synthetic_pe(payload, start_va=start)
    with pytest.raises(ValueError, match="byte hash mismatch"):
        module.verify_function_hashes(
            pe,
            {
                "FUN_test": {
                    "start": start,
                    "end": start + len(payload),
                    "sha256": "0" * 64,
                }
            },
        )


def test_binary_verifier_fails_closed_on_executable_identity_mismatch():
    module = _verifier_module()
    pe = _synthetic_pe(b"\x90")
    with pytest.raises(ValueError, match="unexpected executable MD5"):
        module.verify_function_hashes(pe, {}, expected_md5="0" * 32)
