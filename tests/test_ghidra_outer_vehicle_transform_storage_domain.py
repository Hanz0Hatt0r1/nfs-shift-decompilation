from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_transform_storage_domain.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_transform_storage_domain", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _varnode(
    text: str,
    *,
    space: str = "register",
    offset: str = "0x0",
    size: int = 4,
    constant: bool = False,
    register: bool = True,
    unique: bool = False,
) -> dict:
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _store(address: str, operand: str, *, fallthrough: str, value: str = "EAX") -> dict:
    return {
        "address": address,
        "bytes": "89",
        "mnemonic": "MOV",
        "text": f"MOV {operand},{value}",
        "operands": [operand, value],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "STORE",
                "text": f"STORE ram({operand}) = {value}",
                "output": None,
                "inputs": [
                    _varnode(
                        "RAM",
                        space="const",
                        offset="0x1",
                        constant=True,
                        register=False,
                    ),
                    _varnode("ECX"),
                    _varnode(value),
                ],
            }
        ],
    }


def _ret(address: str) -> dict:
    return {
        "address": address,
        "bytes": "c3",
        "mnemonic": "RET",
        "text": "RET",
        "operands": [],
        "flow_type": "TERMINATOR",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": [],
    }


def _instructions(function: str, *, complex_store: bool = False) -> list[dict]:
    base = int(function, 0)
    first = f"0x{base:08x}"
    second = f"0x{base + 4:08x}"
    end = f"0x{base + 8:08x}"
    operand = "[ECX+EAX*4]" if complex_store else "[ECX+0x10]"
    return [
        _store(first, operand, fallthrough=second),
        _store(second, "[ECX+0x14]", fallthrough=end, value="EDX"),
        _ret(end),
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _ghidra_export(tmp_path: Path, *, drift: str | None = None) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    functions = []
    for address, expected in MODULE._retail_targets().items():
        row = {
            "address": address,
            "name": expected["name"],
            "size": expected["size"],
            "calling_convention": expected["calling_convention"],
            "mnemonic_sha256": expected["mnemonic_sha256"],
            "external": False,
            "thunk": False,
        }
        if drift == address:
            row["mnemonic_sha256"] = "0" * 64
        functions.append(row)
    _write_jsonl(root / "functions.jsonl", functions)
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": MODULE.OUTER_SETTER,
                "instruction": "0x007928f0",
                "to": MODULE.SHARED_POST_TRANSFORM,
                "indirect": False,
            },
            {
                "from_function": MODULE.HDVEHICLE_SETTER,
                "instruction": "0x007634df",
                "to": MODULE.SHARED_POST_TRANSFORM,
                "indirect": False,
            },
            {
                "from_function": MODULE.TRIPLET_SINK,
                "instruction": "0x007afb6c",
                "to": MODULE.TRIPLET_HELPER,
                "indirect": False,
            },
        ],
    )
    return root


def _receiver_report(
    tmp_path: Path,
    *,
    direct: tuple[str, ...] = ("0x007876e0",),
    preclaim: bool = False,
) -> Path:
    origins = {
        "0x007876e0": ["entry:ECX"],
        "0x007afb60": ["memory:[esi+0x20]"],
        "0x00787160": ["memory:[esi+0x24]"],
        MODULE.HDVEHICLE_SETTER: ["memory:[esi+0x20]"],
        "0x007ac2f0": ["memory:[esi+0x20]"],
    }
    rows = []
    for spec in MODULE._receivers.SINK_CALLS:
        callee = spec["callee"]
        is_direct = callee in direct
        same_hd = callee in {"0x007afb60", "0x007ac2f0", MODULE.HDVEHICLE_SETTER}
        if is_direct:
            origins[callee] = ["entry:ECX"]
            same_hd = False
        rows.append(
            {
                **spec,
                "ECX_origins_before_call": origins[callee],
                "ECX_origin_deterministic": True,
                "ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths": is_direct,
                "same_ECX_origin_expression_set_as_HDVehicle_sink": same_hd,
            }
        )
    path = tmp_path / "receivers.json"
    path.write_text(
        json.dumps(
            {
                "format": MODULE.RECEIVER_FORMAT,
                "ready": True,
                "status": "receiver-frontier-ready",
                "sink_receiver_analyses": rows,
                "handoff": {
                    "outer_setter_sink_ECX_provenance_evaluated": True,
                    "outer_setter_sink_ECX_provenance_unambiguous": True,
                    "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
                    "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
                    "BODY0_bind_frame_proof_ready": False,
                    "vehicle_world_transform_ready": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _instruction_export(
    tmp_path: Path,
    functions: tuple[str, ...],
    *,
    complex_for: str | None = None,
) -> Path:
    rows = []
    for function in functions:
        instructions = _instructions(function, complex_store=function == complex_for)
        expected = MODULE._frontier.TARGETS[function]
        rows.append(
            {
                "format": MODULE.INSTRUCTION_FORMAT,
                "program": MODULE.PROGRAM,
                "requested": function,
                "found": True,
                "function": {
                    "address": function,
                    "name": expected["name"],
                    "size": expected["size"],
                    "calling_convention": expected["calling_convention"],
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        )
    path = tmp_path / "instructions.jsonl"
    _write_jsonl(path, rows)
    return path


def test_unique_direct_outer_receiver_becomes_storage_field_frontier(tmp_path):
    report = MODULE.analyze_outer_vehicle_transform_storage_domain(
        _ghidra_export(tmp_path),
        _receiver_report(tmp_path),
        _instruction_export(tmp_path, ("0x007876e0",)),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["status"] == "storage-domain-ready"
    assert report["routing"]["unique_direct_outer_receiver_candidate"] == "0x007876e0"
    assert report["routing"]["HDVehicle_origin_expression_candidates"] == [
        "0x007afb60",
        "0x007ac2f0",
    ]
    assert report["retail_topology"][
        "shared_post_transform_hook_called_from_outer_setter"
    ] is True
    assert report["retail_topology"][
        "shared_post_transform_hook_called_from_HDVehicle_setter"
    ] is True
    assert report["retail_topology"][
        "shared_post_transform_hook_is_unique_outer_owner_signal"
    ] is False

    sink = report["selected_outer_receiver_sinks"][0]
    assert sink["function"] == "0x007876e0"
    assert sink["receiver_relative_store_count"] == 2
    assert sink["receiver_relative_bytes"] == list(range(0x10, 0x18))
    assert all(row["receiver_relative_on_all_reachable_paths"] for row in sink["receiver_relative_stores"])
    assert report["exact_outer_receiver_field_spans"] == [
        {"function": "0x007876e0", "offset": 0x10, "offset_hex": "0x10", "size": 4},
        {"function": "0x007876e0", "offset": 0x14, "offset_hex": "0x14", "size": 4},
    ]
    assert report["handoff"]["outer_vehicle_transform_storage_domain_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["receiver_relative_STORE_promoted_to_VHF_identity"] is False


def test_multiple_direct_outer_receiver_domains_remain_ambiguous(tmp_path):
    direct = ("0x007876e0", "0x007afb60")
    report = MODULE.analyze_outer_vehicle_transform_storage_domain(
        _ghidra_export(tmp_path),
        _receiver_report(tmp_path, direct=direct),
        _instruction_export(tmp_path, direct),
    )

    assert report["status"] == "storage-domain-frontier"
    assert report["routing"]["unique_direct_outer_receiver_domain_ready"] is False
    assert report["handoff"]["outer_vehicle_transform_storage_fields_ready"] is True
    assert report["handoff"]["outer_vehicle_transform_storage_domain_ready"] is False
    assert any(
        row["id"] == "outer-setter-direct-receiver-domain-not-unique"
        for row in report["blockers"]
    )


def test_complex_store_target_keeps_storage_frontier_blocked(tmp_path):
    report = MODULE.analyze_outer_vehicle_transform_storage_domain(
        _ghidra_export(tmp_path),
        _receiver_report(tmp_path),
        _instruction_export(tmp_path, ("0x007876e0",), complex_for="0x007876e0"),
    )

    sink = report["selected_outer_receiver_sinks"][0]
    assert sink["structural_blockers"]
    assert report["handoff"]["outer_vehicle_transform_storage_fields_ready"] is False
    assert any(
        row["id"] == "outer-transform-storage-STORE-structure-ambiguous"
        for row in report["blockers"]
    )


def test_instruction_export_must_match_selected_receiver_set(tmp_path):
    with pytest.raises(ValueError, match="missing selected outer receiver sink"):
        MODULE.analyze_outer_vehicle_transform_storage_domain(
            _ghidra_export(tmp_path),
            _receiver_report(tmp_path, direct=("0x007876e0", "0x007afb60")),
            _instruction_export(tmp_path, ("0x007876e0",)),
        )


def test_shared_post_transform_callgraph_drift_fails_closed(tmp_path):
    root = _ghidra_export(tmp_path)
    rows = [
        json.loads(line)
        for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [
        row
        for row in rows
        if not (
            row["from_function"] == MODULE.HDVEHICLE_SETTER
            and row["to"] == MODULE.SHARED_POST_TRANSFORM
        )
    ]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="required retail transform-domain call edge drift"):
        MODULE.analyze_outer_vehicle_transform_storage_domain(
            root,
            _receiver_report(tmp_path),
            _instruction_export(tmp_path, ("0x007876e0",)),
        )


def test_retail_fingerprint_drift_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="mnemonic_sha256 drift"):
        MODULE.analyze_outer_vehicle_transform_storage_domain(
            _ghidra_export(tmp_path, drift=MODULE.TRIPLET_HELPER),
            _receiver_report(tmp_path),
            _instruction_export(tmp_path, ("0x007876e0",)),
        )


def test_upstream_vhf_identity_preclaim_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims outer_vehicle_root_to_VHF_vehicle_root_ready"):
        MODULE.analyze_outer_vehicle_transform_storage_domain(
            _ghidra_export(tmp_path),
            _receiver_report(tmp_path, preclaim=True),
            _instruction_export(tmp_path, ("0x007876e0",)),
        )
