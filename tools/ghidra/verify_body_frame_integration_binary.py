#!/usr/bin/env python3
"""Verify the retail x86 bytes backing the BODY frame integration contract."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path
from typing import Any


def _load_contract_module():
    path = Path(__file__).resolve().parents[2] / "src" / "physics" / "body_frame_integration_static.py"
    spec = importlib.util.spec_from_file_location("body_frame_integration_static", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_pe32_sections(data: bytes) -> tuple[int, list[dict[str, int | str]]]:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a DOS/PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional = pe_offset + 24
    if optional + optional_size > len(data):
        raise ValueError("truncated PE optional header")
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("expected PE32 optional header")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    section_table = optional + optional_size
    sections: list[dict[str, int | str]] = []
    for index in range(section_count):
        off = section_table + index * 40
        if off + 40 > len(data):
            raise ValueError("truncated PE section table")
        raw_name = data[off : off + 8].split(b"\0", 1)[0]
        sections.append(
            {
                "name": raw_name.decode("ascii", errors="replace"),
                "virtual_size": struct.unpack_from("<I", data, off + 8)[0],
                "virtual_address": struct.unpack_from("<I", data, off + 12)[0],
                "raw_size": struct.unpack_from("<I", data, off + 16)[0],
                "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
            }
        )
    return image_base, sections


def extract_va_range(data: bytes, start: int, end: int) -> bytes:
    if end <= start:
        raise ValueError("invalid VA range")
    image_base, sections = parse_pe32_sections(data)
    start_rva = start - image_base
    end_rva = end - image_base
    if start_rva < 0:
        raise ValueError("VA precedes image base")
    for section in sections:
        section_rva = int(section["virtual_address"])
        raw_size = int(section["raw_size"])
        raw_offset = int(section["raw_offset"])
        if section_rva <= start_rva and end_rva <= section_rva + raw_size:
            offset = raw_offset + (start_rva - section_rva)
            length = end - start
            if offset + length > len(data):
                raise ValueError("VA range maps beyond file bytes")
            return data[offset : offset + length]
    raise ValueError(f"VA range 0x{start:08x}..0x{end:08x} is not file-backed")


def verify_function_hashes(
    data: bytes,
    functions: dict[str, dict[str, Any]],
    *,
    expected_md5: str | None = None,
) -> dict[str, Any]:
    actual_md5 = hashlib.md5(data).hexdigest()
    if expected_md5 is not None and actual_md5 != expected_md5:
        raise ValueError(
            f"unexpected executable MD5: expected {expected_md5}, got {actual_md5}"
        )
    rows = []
    for name, spec in functions.items():
        start = int(spec["start"])
        end = int(spec["end"])
        expected_sha256 = str(spec["sha256"])
        function_bytes = extract_va_range(data, start, end)
        actual_sha256 = hashlib.sha256(function_bytes).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"{name}: byte hash mismatch: expected {expected_sha256}, got {actual_sha256}"
            )
        rows.append(
            {
                "function": name,
                "start": f"0x{start:08x}",
                "end": f"0x{end:08x}",
                "byte_count": len(function_bytes),
                "sha256": actual_sha256,
                "status": "exact-retail-function-bytes-verified",
            }
        )
    return {
        "format": "SHIFT.BodyFrameIntegrationBinaryVerification/1",
        "executable_md5": actual_md5,
        "functions": rows,
        "verified": True,
    }


def verify_retail_executable(path: Path) -> dict[str, Any]:
    module = _load_contract_module()
    data = path.read_bytes()
    return verify_function_hashes(
        data,
        module.FUNCTION_BYTES,
        expected_md5=module.EXECUTABLE_MD5,
    )


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
