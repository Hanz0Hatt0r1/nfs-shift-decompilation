#!/usr/bin/env python3
"""Verify retail PE bytes behind SHIFT.BMWBody0ConstructionBindPose/1."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_contract = _load(
    ROOT / "tools" / "ghidra" / "build_bmw_body0_construction_bind_pose.py",
    "bmw_body0_construction_bind_pose",
)
_pe = _load(
    ROOT / "tools" / "ghidra" / "verify_body_frame_integration_binary.py",
    "body_frame_binary_verifier",
)

FORMAT = "SHIFT.BMWBody0ConstructionBindBinaryVerification/1"


def _va(data: bytes, start: int, end: int) -> bytes:
    return _pe.extract_va_range(data, start, end)


def _verify_rel32_call(data: bytes, callsite: int, target: int) -> dict[str, Any]:
    raw = _va(data, callsite, callsite + 5)
    if len(raw) != 5 or raw[0] != 0xE8:
        raise ValueError(f"0x{callsite:08x}: expected direct rel32 CALL")
    displacement = int.from_bytes(raw[1:], "little", signed=True)
    actual = callsite + 5 + displacement
    if actual != target:
        raise ValueError(
            f"0x{callsite:08x}: CALL target drift: expected 0x{target:08x}, got 0x{actual:08x}"
        )
    return {
        "callsite": f"0x{callsite:08x}",
        "target": f"0x{target:08x}",
        "bytes": raw.hex(),
        "verified": True,
    }


def verify_retail_executable(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    actual_md5 = hashlib.md5(data).hexdigest()
    if actual_md5 != _contract.EXECUTABLE_MD5:
        raise ValueError(
            f"unexpected executable MD5: expected {_contract.EXECUTABLE_MD5}, got {actual_md5}"
        )

    functions = _pe.verify_function_hashes(
        data,
        _contract.FUNCTION_BYTES,
        expected_md5=_contract.EXECUTABLE_MD5,
    )

    signatures: list[dict[str, Any]] = []
    for name, spec in _contract.MACHINE_SIGNATURES.items():
        start = int(spec["start"])
        end = int(spec["end"])
        expected = bytes.fromhex(str(spec["hex"]))
        actual = _va(data, start, end)
        if actual != expected:
            raise ValueError(
                f"{name}: machine signature drift at 0x{start:08x}..0x{end:08x}"
            )
        signatures.append(
            {
                "name": name,
                "start": f"0x{start:08x}",
                "end": f"0x{end:08x}",
                "bytes": actual.hex(),
                "sha256": hashlib.sha256(actual).hexdigest(),
                "verified": True,
            }
        )

    address_by_name = {
        name: int(spec["start"])
        for name, spec in _contract.FUNCTION_BYTES.items()
    }
    calls = [
        _verify_rel32_call(
            data,
            int(row["callsite"]),
            address_by_name[str(row["callee"])],
        )
        for row in _contract.DIRECT_CALLS
    ]

    return {
        "format": FORMAT,
        "verified": True,
        "executable_md5": actual_md5,
        "function_hash_verification": functions,
        "machine_signatures": signatures,
        "direct_calls": calls,
        "proofs": {
            "FUN_007b6900_calls_FUN_007b3670": True,
            "FUN_007b3670_copies_descriptor_origin_to_persistent_BODY": True,
            "FUN_007b3670_forwards_descriptor_ori_to_FUN_007bbb10": True,
            "FUN_007bbb10_forwards_ori_to_basis_builder": True,
            "x87_fsin_fcos_opcodes_verified": True,
            "BODY_count_increment_follows_pose_initialization": True,
        },
        "scope": {
            "original_game_executed": False,
            "runtime_capture_used": False,
            "binary_read_only": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = verify_retail_executable(args.executable)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
