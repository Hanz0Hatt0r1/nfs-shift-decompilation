#!/usr/bin/env python3
"""Close the resolved indirect render-manager +0xca4 branch from exact retail PE bytes.

This proof is intentionally narrow.  The preceding indirect-dispatch proof resolves
all frozen manager calls to exactly two entries.  For the retail executable those
entries are tiny branch-free getter/setter bodies.  We decode only those two exact
machine shapes, prove their only ECX-relative access is +0xdac, and join that
negative result with the already-negative direct manager-method branch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
_D3D9_SRC = _REPO_ROOT / "src" / "graphics" / "d3d9"
for _path in (_SCRIPT_DIR, _D3D9_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from d3d9_pe_evidence import PEImage, parse_pe
import analyze_player_vehicle_render_manager_indirect_method_ca4_access as _pcode

FORMAT = "SHIFT.PlayerVehicleRenderManagerIndirectMethodCa4MachineNegative/1"
PROGRAM = _pcode.PROGRAM
PE_MD5 = _pcode.PE_MD5
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE = 0x00400000
MACHINE_I386 = 0x014C
FIELD_OFFSET = 0xCA4
OBSERVED_OFFSET = 0xDAC

GETTER = 0x0045F620
SETTER = 0x0045F630
EXPECTED_TARGETS = {f"0x{GETTER:08x}", f"0x{SETTER:08x}"}
GETTER_SIZE = 7
SETTER_SIZE = 16


def _hex_addr(value: int) -> str:
    return f"0x{value:08x}"


def _decode_getter(payload: bytes) -> dict[str, Any]:
    # MOV EAX,[ECX+disp32] ; RET
    if len(payload) != GETTER_SIZE or payload[:2] != b"\x8b\x81" or payload[6:] != b"\xc3":
        raise ValueError("0x0045f620 machine body drift")
    displacement = int.from_bytes(payload[2:6], "little", signed=True)
    return {
        "entry": _hex_addr(GETTER),
        "body_hex": payload.hex(),
        "body_size": len(payload),
        "decoded_instructions": [
            {"address": _hex_addr(GETTER), "mnemonic": "MOV", "operands": ["EAX", f"dword ptr [ECX + 0x{displacement:x}]"]},
            {"address": _hex_addr(GETTER + 6), "mnemonic": "RET", "operands": []},
        ],
        "memory_accesses": [
            {
                "instruction": _hex_addr(GETTER),
                "kind": "read",
                "base_register": "ECX",
                "displacement": displacement,
                "displacement_hex": f"+0x{displacement:x}",
            }
        ],
        "branch_or_call_count": 0,
        "terminal_return": True,
        "cfg_complete_for_negative_closure": True,
    }


def _decode_setter(payload: bytes) -> dict[str, Any]:
    # PUSH EBP ; MOV EBP,ESP ; MOV EAX,[EBP+8] ; MOV [ECX+disp32],EAX ; POP EBP ; RET 4
    prefix = bytes.fromhex("558bec8b45088981")
    suffix = bytes.fromhex("5dc20400")
    if len(payload) != SETTER_SIZE or payload[:8] != prefix or payload[12:] != suffix:
        raise ValueError("0x0045f630 machine body drift")
    displacement = int.from_bytes(payload[8:12], "little", signed=True)
    return {
        "entry": _hex_addr(SETTER),
        "body_hex": payload.hex(),
        "body_size": len(payload),
        "decoded_instructions": [
            {"address": _hex_addr(SETTER), "mnemonic": "PUSH", "operands": ["EBP"]},
            {"address": _hex_addr(SETTER + 1), "mnemonic": "MOV", "operands": ["EBP", "ESP"]},
            {"address": _hex_addr(SETTER + 3), "mnemonic": "MOV", "operands": ["EAX", "dword ptr [EBP + 0x8]"]},
            {"address": _hex_addr(SETTER + 6), "mnemonic": "MOV", "operands": [f"dword ptr [ECX + 0x{displacement:x}]", "EAX"]},
            {"address": _hex_addr(SETTER + 12), "mnemonic": "POP", "operands": ["EBP"]},
            {"address": _hex_addr(SETTER + 13), "mnemonic": "RET", "operands": ["0x4"]},
        ],
        "memory_accesses": [
            {
                "instruction": _hex_addr(SETTER + 3),
                "kind": "read",
                "base_register": "EBP",
                "displacement": 8,
                "displacement_hex": "+0x8",
            },
            {
                "instruction": _hex_addr(SETTER + 6),
                "kind": "write",
                "base_register": "ECX",
                "displacement": displacement,
                "displacement_hex": f"+0x{displacement:x}",
            },
        ],
        "branch_or_call_count": 0,
        "terminal_return": True,
        "cfg_complete_for_negative_closure": True,
    }


def _target_report(image: PEImage, entry: int, size: int, decoder) -> dict[str, Any]:
    section = image.section_for_va(entry)
    file_offset = image.file_offset_for_va(entry)
    payload = image.read_virtual(entry, size)
    if section is None or section.name != ".text":
        raise ValueError(f"{_hex_addr(entry)} is not in retail .text")
    if file_offset is None or payload is None:
        raise ValueError(f"{_hex_addr(entry)} is not file-backed")
    decoded = decoder(payload)
    ecx_accesses = [item for item in decoded["memory_accesses"] if item["base_register"] == "ECX"]
    ca4 = [item for item in ecx_accesses if item["displacement"] == FIELD_OFFSET]
    decoded.update(
        {
            "section": section.name,
            "file_offset": file_offset,
            "ecx_relative_access_count": len(ecx_accesses),
            "ca4_access_count": len(ca4),
            "ca4_access_found": bool(ca4),
        }
    )
    return decoded


def analyze_image(
    image: PEImage,
    *,
    executable_md5: str,
    executable_sha256: str,
    require_retail_identity: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if image.image_base != IMAGE_BASE:
        errors.append(f"image-base:{image.image_base:#x}!={IMAGE_BASE:#x}")
    if image.machine != MACHINE_I386:
        errors.append(f"machine:{image.machine:#x}!={MACHINE_I386:#x}")
    if require_retail_identity and executable_md5.lower() != PE_MD5:
        errors.append(f"md5:{executable_md5.lower()}!={PE_MD5}")
    if require_retail_identity and executable_sha256.lower() != PE_SHA256:
        errors.append(f"sha256:{executable_sha256.lower()}!={PE_SHA256}")
    if errors:
        raise ValueError("retail executable identity drift: " + "; ".join(errors))

    getter = _target_report(image, GETTER, GETTER_SIZE, _decode_getter)
    setter = _target_report(image, SETTER, SETTER_SIZE, _decode_setter)
    targets = [getter, setter]
    negative = all(
        item["cfg_complete_for_negative_closure"]
        and item["terminal_return"]
        and item["branch_or_call_count"] == 0
        and item["ca4_access_count"] == 0
        for item in targets
    )
    observed_ecx_offsets = sorted(
        {
            access["displacement"]
            for target in targets
            for access in target["memory_accesses"]
            if access["base_register"] == "ECX"
        }
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "proven" if negative else "blocked",
        "ready": negative,
        "evidence_state": "proven-static-negative" if negative else "contradicted",
        "retail": {
            "program": PROGRAM,
            "md5": executable_md5.lower(),
            "sha256": executable_sha256.lower(),
            "image_base": _hex_addr(image.image_base),
            "machine": f"0x{image.machine:04x}",
        },
        "subject": {
            "resolved_indirect_target_set": sorted(EXPECTED_TARGETS),
            "field_hypothesis_offset": FIELD_OFFSET,
            "field_hypothesis_offset_hex": "+0xca4",
        },
        "analysis": {
            "targets": targets,
            "target_count": len(targets),
            "cfg_complete_target_count": sum(bool(item["cfg_complete_for_negative_closure"]) for item in targets),
            "ca4_access_count": sum(int(item["ca4_access_count"]) for item in targets),
            "observed_ecx_relative_offsets": observed_ecx_offsets,
            "observed_ecx_relative_offsets_hex": [f"+0x{value:x}" for value in observed_ecx_offsets],
        },
        "claim": {
            "indirect_manager_method_ca4_branch_negative": negative,
            "all_resolved_targets_cfg_complete": all(item["cfg_complete_for_negative_closure"] for item in targets),
            "all_resolved_targets_branch_free": all(item["branch_or_call_count"] == 0 for item in targets),
            "only_observed_ecx_relative_offset_is_dac": observed_ecx_offsets == [OBSERVED_OFFSET],
        },
        "limits": [
            "does not prove mPlayerVehicleRenderables ownership or a VHF root/frame",
            "does not prove SHIFT.BMWBody0BindFrameProof/1",
            "does not infer scheduler, physics producer, camera, or vehicle world-transform semantics",
            "applies only to the exact two targets resolved by SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1",
        ],
    }


def analyze_executable_bytes(data: bytes) -> dict[str, Any]:
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    image = parse_pe(data)
    return analyze_image(
        image,
        executable_md5=md5,
        executable_sha256=sha256,
        require_retail_identity=True,
    )


def _validate_upstream_and_compose(
    direct_negative_path: Path,
    indirect_dispatch_path: Path,
    machine: Mapping[str, Any],
) -> dict[str, Any]:
    direct = _pcode._validate_direct_negative(direct_negative_path)
    indirect, targets = _pcode._validate_indirect(indirect_dispatch_path)
    if set(targets) != EXPECTED_TARGETS:
        raise ValueError(f"resolved indirect target set drift: expected={sorted(EXPECTED_TARGETS)}, got={sorted(targets)}")
    if machine.get("format") != FORMAT or machine.get("ready") is not True:
        raise ValueError("machine negative proof is not ready")
    subject = machine.get("subject")
    claim = machine.get("claim")
    if not isinstance(subject, Mapping) or set(subject.get("resolved_indirect_target_set") or []) != EXPECTED_TARGETS:
        raise ValueError("machine target set drift")
    if not isinstance(claim, Mapping) or claim.get("indirect_manager_method_ca4_branch_negative") is not True:
        raise ValueError("machine proof does not close indirect +0xca4 branch")

    return {
        **dict(machine),
        "inputs": {
            "direct_manager_method_ca4": {
                "format": direct["format"],
                "ready": False,
                "targeted_direct_callee_count": 17,
            },
            "indirect_dispatch": {
                "format": indirect["format"],
                "ready": True,
                "resolved_target_set": sorted(targets),
            },
            "retail_machine_body": FORMAT,
        },
        "handoff": {
            "direct_manager_method_ca4_branch_negative": True,
            "indirect_manager_method_ca4_branch_negative": True,
            "manager_method_ca4_hypothesis_closed": True,
            "player_vehicle_renderables_field_runtime_access_ready": False,
            "bmw_body0_bind_frame_proof_ready": False,
            "next_frontier": {
                "kind": "canonical-body0-construction-bind-provenance",
                "functions": ["0x007b3670", "0x007bba90", "0x007bbb10", "0x007bbb60"],
                "neighbors_added": False,
            },
        },
        "consumer": "Process 1 P1.1 must leave the manager +0xca4 hypothesis and continue the canonical BODY0 construction/bind provenance lane",
    }


def analyze(direct_negative_path: Path, indirect_dispatch_path: Path, executable_path: Path) -> dict[str, Any]:
    machine = analyze_executable_bytes(executable_path.read_bytes())
    result = _validate_upstream_and_compose(direct_negative_path, indirect_dispatch_path, machine)
    result["retail"]["path"] = str(executable_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direct_negative", type=Path, help="negative SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1 JSON")
    parser.add_argument("indirect_dispatch", type=Path, help="positive SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1 JSON")
    parser.add_argument("executable", type=Path, help="retail SHIFT.exe")
    parser.add_argument("--json-out", type=Path, help="write proof JSON here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = analyze(args.direct_negative, args.indirect_dispatch, args.executable)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
