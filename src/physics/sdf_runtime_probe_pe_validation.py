"""Validate retail SHIFT.exe PE mapping for the SDF runtime probe."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from d3d9_pe_evidence import PEImage, parse_pe
from sdf_runtime_probe_runtime import FUNCTIONS, IMAGE_BASE

FORMAT = "SHIFT.SDFRuntimeProbePEValidation/1"

EXPECTED_EXECUTABLE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

EXPECTED_PROLOGUES = {
    "frame_entry": bytes.fromhex("558bec51568bf1837e48005775368b4e"),
    "builtin_solver": bytes.fromhex("558bec83ec208b5510535633f685d257"),
    "post_solve": bytes.fromhex("538bdc83ec0883e4f883c404558b6b04"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_probe_targets(
    image: PEImage,
    *,
    expected_image_base: int = IMAGE_BASE,
) -> dict[str, Any]:
    errors: list[str] = []
    targets: dict[str, Any] = {}
    if image.image_base != int(expected_image_base):
        errors.append(
            f"image-base:{image.image_base:#x}!={int(expected_image_base):#x}"
        )
    if image.machine != 0x014C:
        errors.append(f"machine:{image.machine:#x}!=0x14c")

    text_section_names: set[str] = set()
    for name, address in FUNCTIONS.items():
        section = image.section_for_va(address)
        file_offset = image.file_offset_for_va(address)
        prologue = image.read_virtual(address, len(EXPECTED_PROLOGUES[name]))
        actual_hex = None if prologue is None else prologue.hex()
        expected = EXPECTED_PROLOGUES[name]
        target = {
            "address": f"0x{address:08x}",
            "section": section.name if section else None,
            "file_offset": file_offset,
            "file_backed": file_offset is not None and prologue is not None,
            "actual_prologue": actual_hex,
            "expected_prologue": expected.hex(),
            "matches": prologue == expected,
        }
        targets[name] = target
        if section is not None:
            text_section_names.add(section.name)
        if not target["file_backed"]:
            errors.append(f"{name}:not-file-backed")
        if not target["matches"]:
            errors.append(f"{name}:prologue-mismatch")

    if text_section_names != {".text"}:
        errors.append(
            "target-sections:" + ",".join(sorted(text_section_names))
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "validated" if not errors else "blocked",
        "ready": not errors,
        "image_base": image.image_base,
        "machine": image.machine,
        "targets": targets,
        "errors": errors,
    }


def validate_probe_executable_bytes(
    data: bytes,
    *,
    expected_sha256: str | None = EXPECTED_EXECUTABLE_SHA256,
) -> dict[str, Any]:
    digest = sha256(data)
    image = parse_pe(data)
    result = validate_probe_targets(image)
    if expected_sha256 is not None and digest != expected_sha256:
        result["ready"] = False
        result["status"] = "blocked"
        result["errors"] = list(result["errors"]) + [
            f"sha256:{digest}!={expected_sha256}"
        ]
    result["sha256"] = digest
    result["path"] = None
    return result


def validate_probe_executable_file(
    path: str | Path,
    *,
    expected_sha256: str | None = EXPECTED_EXECUTABLE_SHA256,
) -> dict[str, Any]:
    source = Path(path)
    result = validate_probe_executable_bytes(
        source.read_bytes(),
        expected_sha256=expected_sha256,
    )
    result["path"] = str(source)
    return result


def describe_probe_pe_validation_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "executable": {
            "sha256": EXPECTED_EXECUTABLE_SHA256,
            "machine": "0x014c/i386",
            "image_base": "0x00400000",
        },
        "targets": {
            name: {
                "address": f"0x{address:08x}",
                "expected_prologue": EXPECTED_PROLOGUES[name].hex(),
                "section": ".text",
            }
            for name, address in FUNCTIONS.items()
        },
        "fail_closed": [
            "wrong SHA-256",
            "wrong image base",
            "wrong machine",
            "target not file-backed",
            "target prologue mismatch",
        ],
        "limitations": [
            "This validates the supplied retail executable against known source/PE evidence.",
            "It does not attach a debugger or inspect runtime ASLR state.",
        ],
    }


__all__ = [
    "EXPECTED_EXECUTABLE_SHA256",
    "EXPECTED_PROLOGUES",
    "validate_probe_targets",
    "validate_probe_executable_bytes",
    "validate_probe_executable_file",
    "describe_probe_pe_validation_contract",
]
