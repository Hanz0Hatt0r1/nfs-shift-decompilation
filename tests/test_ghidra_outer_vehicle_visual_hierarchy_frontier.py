from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_visual_hierarchy_frontier.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_visual_hierarchy_frontier", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _pcode(opcode: str, text: str):
    return {"opcode": opcode, "text": text}


def _ins(address, mnemonic, operands=None, *, flows=None, fallthrough=None, flow_type="FALL_THROUGH", pcode=None):
    operands = [] if operands is None else operands
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "flows": [] if flows is None else flows,
        "fallthrough": fallthrough,
        "flow_type": flow_type,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _row(address, instructions):
    return {
        "format": m.INSTRUCTION_FORMAT,
        "program": m.PROGRAM,
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _make_upstream(path: Path):
    return _write_json(
        path,
        {
            "format": m.UPSTREAM_FORMAT,
            "ready": True,
            "chassis_init": {
                "function": m.CHASSIS_INIT,
                "embedded_owner_edges": [
                    {
                        "offset": "+0x534",
                        "callees": ["0x0049f980", "0x007a5a40", m.VISUAL_SETUP],
                    }
                ],
            },
            "handoff": {
                "HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain": True,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            },
        },
    )


def _make_db(root: Path, *, mutate=None):
    root.mkdir()
    _write_json(
        root / "binary.json",
        {
            "format": m.DB_FORMAT,
            "program_name": m.PROGRAM,
            "executable_md5": m.PE_MD5,
        },
    )
    function_rows = [
        {
            "address": address,
            "name": "thunk_FUN_00d5bf10" if address == m.RESOLVER_THUNK else "FUN_" + address[2:],
            "external": False,
            "thunk": address == m.RESOLVER_THUNK,
            "mnemonic_sha256": fingerprint,
        }
        for address, fingerprint in m.FINGERPRINTS.items()
    ]
    string_rows = [
        {
            "address": address,
            "value": value,
            "xrefs": [xref],
            "functions": [m.VISUAL_SETUP],
        }
        for address, (value, xref) in m.WHEEL_STRING_WITNESSES.items()
    ]
    callgraph_rows = [
        {
            "from_function": m.CHASSIS_INIT,
            "from_name": "FUN_007ac4d0",
            "instruction": "0x007accc3",
            "to": m.VISUAL_SETUP,
            "to_name": "FUN_007a3d60",
            "indirect": False,
        },
        {
            "from_function": m.VISUAL_SETUP,
            "from_name": "FUN_007a3d60",
            "instruction": m.RESOLVER_CALLSITE,
            "to": m.RESOLVER_THUNK,
            "to_name": "thunk_FUN_00d5bf10",
            "indirect": False,
        },
    ]
    if mutate:
        mutate(function_rows, string_rows, callgraph_rows)
    _write_jsonl(root / "functions.jsonl", function_rows)
    _write_jsonl(root / "strings_xrefs.jsonl", string_rows)
    _write_jsonl(root / "callgraph.jsonl", callgraph_rows)
    return root


def _make_instructions(path: Path, *, mutate=None):
    visual = [
        _ins(m.VISUAL_SETUP, "MOV", ["ESI", "ECX"], fallthrough="0x007a401f"),
        _ins("0x007a401f", "MOV", ["ECX", "ESI"], fallthrough=m.RESOLVER_CALLSITE),
        _ins(
            m.RESOLVER_CALLSITE,
            "CALL",
            [m.RESOLVER_THUNK],
            flows=[m.RESOLVER_THUNK],
            fallthrough="0x007a402f",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x0047bdf0")],
        ),
        _ins(
            "0x007a402f",
            "MOV",
            ["dword ptr [ESI + 0x20]", "EAX"],
            fallthrough="0x007a4032",
            pcode=[_pcode("STORE", "STORE ram(ESI + 0x20), EAX")],
        ),
        _ins("0x007a4032", "RET", [], fallthrough=None, flow_type="TERMINATOR"),
    ]
    resolver = [
        _ins(
            m.RESOLVER,
            "MOV",
            ["EAX", "dword ptr [ECX + 0x10]"],
            fallthrough="0x00d5bf15",
            pcode=[_pcode("LOAD", "EAX = LOAD ram(ECX + 0x10)")],
        ),
        _ins(
            "0x00d5bf15",
            "MOV",
            ["dword ptr [ECX + 0x14]", "EDX"],
            fallthrough="0x00d5bf19",
            pcode=[_pcode("STORE", "STORE ram(ECX + 0x14), EDX")],
        ),
        _ins("0x00d5bf19", "RET", [], fallthrough=None, flow_type="TERMINATOR"),
    ]
    rows = [_row(m.VISUAL_SETUP, visual), _row(m.RESOLVER, resolver)]
    if mutate:
        mutate(rows)
    return _write_jsonl(path, rows)


def _fixture(tmp_path: Path, *, db_mutate=None, ins_mutate=None):
    return (
        _make_db(tmp_path / "db", mutate=db_mutate),
        _make_upstream(tmp_path / "upstream.json"),
        _make_instructions(tmp_path / "instructions.jsonl", mutate=ins_mutate),
    )


def test_builds_finite_visual_resolver_frontier_without_vhf_identity_claim(tmp_path):
    db, upstream, instructions = _fixture(tmp_path)
    report = m.analyze(db, upstream, instructions)

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["anchors"]["visual_setup_receiver_from_upstream"] == "car-body/CHASSIS +0x534"
    assert len(report["anchors"]["wheel_LODA_strings"]) == 4

    resolver = report["resolver_frontier"]
    assert resolver["callsite"] == m.RESOLVER_CALLSITE
    assert resolver["thunk"] == m.RESOLVER_THUNK
    assert resolver["concrete_function"] == m.RESOLVER
    assert resolver["registers_before_call"]["ECX"]["origins"] == ["entry:ECX"]
    assert resolver["registers_before_call"]["ESI"]["origins"] == ["entry:ECX"]
    assert resolver["lexical_direct_memory_store_from_EAX_count"] == 1
    assert resolver["lexical_EAX_consumers_are_semantic_proof"] is False
    assert resolver["resolver_register_relative_accesses"]["syntactic_register_relative_access_count"] == 2
    assert set(resolver["resolver_register_relative_accesses"]["by_base_register"]) == {"ECX"}

    assert report["handoff"]["outer_vehicle_car_body_plus_0x534_to_visual_setup_ready"] is True
    assert report["handoff"]["vehicle_visual_LOD_domain_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["resolver_result_promoted_to_VHF_node_identity"] is False


def test_rejects_resolver_callsite_target_drift(tmp_path):
    def mutate(rows):
        for row in rows:
            if row["function"]["address"] == m.VISUAL_SETUP:
                for instruction in row["instructions"]:
                    if instruction["address"] == m.RESOLVER_CALLSITE:
                        instruction["flows"] = ["0x00400000"]
                        instruction["operands"] = ["0x00400000"]

    db, upstream, instructions = _fixture(tmp_path, ins_mutate=mutate)
    with pytest.raises(ValueError, match="exact resolver CALL"):
        m.analyze(db, upstream, instructions)


def test_rejects_missing_wheel_loda_witness(tmp_path):
    def mutate(_functions, strings, _callgraph):
        strings.pop()

    db, upstream, instructions = _fixture(tmp_path, db_mutate=mutate)
    with pytest.raises(ValueError, match="wheel LODA witness drift"):
        m.analyze(db, upstream, instructions)


def test_rejects_duplicate_chassis_to_visual_setup_edge(tmp_path):
    def mutate(_functions, _strings, callgraph):
        callgraph.append(dict(callgraph[0], instruction="0x007acccc"))

    db, upstream, instructions = _fixture(tmp_path, db_mutate=mutate)
    with pytest.raises(ValueError, match="exactly one direct chassis-init"):
        m.analyze(db, upstream, instructions)
