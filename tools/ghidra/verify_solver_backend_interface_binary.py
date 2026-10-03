#!/usr/bin/env python3
"""Verify exact PE evidence for the static solver-backend interface contract."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path
from typing import Any


def _load_extract_va_range():
    path = Path(__file__).with_name("verify_body_frame_integration_binary.py")
    spec = importlib.util.spec_from_file_location(
        "verify_body_frame_integration_binary_for_solver_backend", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.extract_va_range


extract_va_range = _load_extract_va_range()


def _load_contract_module():
    path = Path(__file__).resolve().parents[2] / "src" / "physics" / "solver_backend_interface_static.py"
    spec = importlib.util.spec_from_file_location("solver_backend_interface_static", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def verify_solver_backend_binary(data: bytes, contract: dict[str, Any]) -> dict[str, Any]:
    expected_md5 = contract["source"]["executable_md5"]
    actual_md5 = hashlib.md5(data).hexdigest()
    if actual_md5 != expected_md5:
        raise ValueError(
            f"unexpected executable MD5: expected {expected_md5}, got {actual_md5}"
        )

    function_rows = []
    module = _load_contract_module()
    for name, spec in module.FUNCTION_BYTES.items():
        start = int(spec["start"])
        end = int(spec["end"])
        payload = extract_va_range(data, start, end)
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != spec["sha256"]:
            raise ValueError(
                f"{name}: byte hash mismatch: expected {spec['sha256']}, got {actual_sha256}"
            )
        function_rows.append(
            {
                "function": name,
                "start": f"0x{start:08x}",
                "end": f"0x{end:08x}",
                "byte_count": len(payload),
                "sha256": actual_sha256,
                "status": "exact-retail-function-bytes-verified",
            }
        )

    table_rows = []
    for backend in contract["backend_candidates"]:
        address = int(backend["vtable"], 16)
        payload = extract_va_range(data, address, address + 12 * 4)
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != backend["vtable_sha256"]:
            raise ValueError(
                f"{backend['vtable']}: vtable hash mismatch: expected "
                f"{backend['vtable_sha256']}, got {actual_sha256}"
            )
        pointers = tuple(f"0x{value:08x}" for value in struct.unpack("<12I", payload))
        if pointers != tuple(backend["slots"]):
            raise ValueError(f"{backend['vtable']}: vtable slot target mismatch")
        table_rows.append(
            {
                "registry_index": backend["registry_index"],
                "vtable": backend["vtable"],
                "sha256": actual_sha256,
                "slots": pointers,
                "status": "exact-retail-vtable-bytes-verified",
            }
        )

    dispatch_windows = (
        {
            "instruction": "0x007b3f8c",
            "start": 0x007B3F84,
            "end": 0x007B3F8E,
            "expected_hex": "8b4e488b118b4220ffd0",
            "vtable_offset": "0x20",
            "slot": 8,
        },
        {
            "instruction": "0x007b4102",
            "start": 0x007B40FA,
            "end": 0x007B4104,
            "expected_hex": "8b4e488b118b4218ffd0",
            "vtable_offset": "0x18",
            "slot": 6,
        },
    )
    dispatch_rows = []
    for row in dispatch_windows:
        payload = extract_va_range(data, row["start"], row["end"])
        actual_hex = payload.hex()
        if actual_hex != row["expected_hex"]:
            raise ValueError(
                f"{row['instruction']}: indirect dispatch bytes mismatch: "
                f"expected {row['expected_hex']}, got {actual_hex}"
            )
        dispatch_rows.append(
            {
                "instruction": row["instruction"],
                "vtable_offset": row["vtable_offset"],
                "slot": row["slot"],
                "bytes_hex": actual_hex,
                "status": "exact-indirect-dispatch-sequence-verified",
            }
        )

    return {
        "format": "SHIFT.SolverBackendInterfaceBinaryVerification/1",
        "executable_md5": actual_md5,
        "functions": function_rows,
        "vtables": table_rows,
        "dispatch_sequences": dispatch_rows,
        "verified": True,
    }


def verify_retail_executable(path: Path) -> dict[str, Any]:
    module = _load_contract_module()
    contract = module.build_contract()
    module.validate_contract(contract)
    return verify_solver_backend_binary(path.read_bytes(), contract)


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
