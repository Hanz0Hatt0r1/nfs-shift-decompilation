from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_actual_additional_mass_writer_frontier.py"
SPEC = importlib.util.spec_from_file_location("offset33b_actual_mass_writer", TOOL)
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


def _ins(
    address: str,
    mnemonic: str,
    operands: list[str],
    *,
    fallthrough: str | None = None,
    flows: list[str] | None = None,
    flow_type: str = "FALL_THROUGH",
    pcode: list[dict] | None = None,
) -> dict:
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {', '.join(operands)}".strip(),
        "operands": operands,
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _call(address: str, target: str, fallthrough: str | None) -> dict:
    return _ins(
        address,
        "CALL",
        [target],
        fallthrough=fallthrough,
        flows=[target],
        flow_type="UNCONDITIONAL_CALL",
    )


def _ret(address: str) -> dict:
    return _ins(address, "RET", [], flow_type="TERMINATOR")


def _store(address: str, base: str, displacement: int, value: int, fallthrough: str) -> dict:
    return _ins(
        address,
        "MOV",
        [f"[{base} + 0x{displacement:x}]", f"0x{value:x}"],
        fallthrough=fallthrough,
        pcode=[
            {
                "opcode": "STORE",
                "text": "STORE ram, target, value",
                "output": None,
                "inputs": [
                    _varnode("ram", space="constant", offset="0x1", constant=True, register=False),
                    _varnode("target", space="unique", offset="0x100", register=False, unique=True),
                    _varnode(
                        f"0x{value:x}",
                        space="constant",
                        offset=f"0x{value:x}",
                        constant=True,
                        register=False,
                    ),
                ],
            }
        ],
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _retail_root(tmp_path: Path, *, bad_md5: bool = False) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps(
            {
                "program_name": MODULE.PROGRAM,
                "executable_md5": "bad" if bad_md5 else MODULE.PE_MD5,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        root / "functions.jsonl",
        [
            {
                "address": address,
                "name": spec["name"],
                "namespace": "Global",
                "size": spec["size"],
                "thunk": False,
                "external": False,
                "calling_convention": spec["calling_convention"],
                "signature": "synthetic",
                "parameters": [],
                "mnemonic_sha256": spec["mnemonic_sha256"],
            }
            for address, spec in MODULE.FUNCTIONS.items()
        ],
    )
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": source,
                "from_name": MODULE.FUNCTIONS[source]["name"],
                "instruction": instruction,
                "to": target,
                "to_name": MODULE.FUNCTIONS[target]["name"],
                "indirect": False,
            }
            for source, instruction, target, _ in MODULE.REQUIRED_CALLS
        ],
    )
    return root


def _rows(*, vehicle_delta: int = 0x340, direct_store: bool = True) -> dict[str, list[dict]]:
    participant: list[dict] = [
        _ins("0x0072ed20", "MOV", ["ESI", "ECX"], fallthrough="0x0072ed30"),
    ]
    if direct_store:
        participant.append(_store("0x0072ed30", "ESI", 0xBA0, 0, "0x0072ed40"))
    else:
        participant.append(_ins("0x0072ed30", "NOP", [], fallthrough="0x0072ed40"))
    participant.extend(
        [
            _ins(
                "0x0072ed40",
                "LEA",
                ["ECX", f"[ESI + 0x{vehicle_delta:x}]"],
                fallthrough="0x0072ed57",
            ),
            _call("0x0072ed57", "0x0079c1c0", "0x0072ed60"),
            _ret("0x0072ed60"),
        ]
    )

    return {
        "0x007125e0": [
            _ins("0x007125e0", "MOV", ["ESI", "ECX"], fallthrough="0x0071262b"),
            _call("0x0071262b", "0x0072ed20", "0x00712630"),
            _ret("0x00712630"),
        ],
        "0x0072ed20": participant,
        "0x0079c1c0": [
            _ins("0x0079c1c0", "MOV", ["ESI", "ECX"], fallthrough="0x0079c1d8"),
            _ins("0x0079c1d8", "MOV", ["ECX", "ESI"], fallthrough="0x0079c1e1"),
            _call("0x0079c1e1", "0x0079bfd0", "0x0079c1e8"),
            _ret("0x0079c1e8"),
        ],
        "0x0079bfd0": [
            _ins("0x0079bfd0", "MOV", ["ESI", "ECX"], fallthrough="0x0079bfe8"),
            _ins("0x0079bfe8", "MOV", ["ECX", "ESI"], fallthrough="0x0079bff6"),
            _call("0x0079bff6", "0x0074ea70", "0x0079bffd"),
            _ret("0x0079bffd"),
        ],
    }


def _instruction_export(tmp_path: Path, rows: dict[str, list[dict]]) -> Path:
    path = tmp_path / "instructions.jsonl"
    payload: list[dict] = []
    for address, spec in MODULE.FUNCTIONS.items():
        instructions = rows[address]
        payload.append(
            {
                "format": MODULE.INSTRUCTION_FORMAT,
                "program": MODULE.PROGRAM,
                "requested": spec["name"],
                "found": True,
                "function": {
                    "address": address,
                    "name": spec["name"],
                    "size": spec["size"],
                    "calling_convention": spec["calling_convention"],
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        )
    _write_jsonl(path, payload)
    return path


def test_proves_affine_vehicle_handoff_and_finds_actual_participant_writer(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, _rows()),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    relation = report["object_relation"]
    assert relation["participant_to_vehicle_affine_receiver_ready"] is True
    assert relation["participant_to_vehicle_callsite"]["ECX_origins_before_call"] == [
        "entry:ECX+0x340"
    ]
    assert relation["vehicle_to_base_receiver_ready"] is True

    handoff = report["handoff"]
    assert handoff["actual_additional_mass_direct_writer_found"] is True
    assert handoff["actual_additional_mass_numeric_value_ready"] is False
    assert handoff["offset33b_additional_mass_bootstrap_zero_ready"] is False
    assert handoff["BMW_numeric_offset33b_ready"] is False

    writers = report["analysis"]["direct_target_writers"]
    assert len(writers) == 1
    assert writers[0]["function"] == MODULE.ACTUAL_PARTICIPANT
    assert writers[0]["displacement"] == 0xBA0
    assert writers[0]["base_register_origins"] == ["entry:ECX"]
    assert writers[0]["terminal_root_kinds"] == ["constant"]
    assert writers[0]["numeric_value_proven"] is False
    assert report["scope"]["manager_record_zero_assumption_reused"] is False


def test_no_direct_writer_emits_same_receiver_forward_worklist(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, _rows(direct_store=False)),
    )
    assert report["ready"] is True
    assert report["analysis"]["direct_target_writer_count"] == 0
    calls = report["analysis"]["same_receiver_forward_worklist"]
    assert any(
        row["function"] == MODULE.VEHICLE_BASE_CTOR and row["callee"] == "0x0074ea70"
        for row in calls
    )
    assert report["blockers"][-1]["id"] == "vehicle-plus-0x860-direct-writer-not-in-constructor-chain"


def test_wrong_embedded_vehicle_delta_fails_closed(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
        _retail_root(tmp_path),
        _instruction_export(tmp_path, _rows(vehicle_delta=0x344)),
    )
    assert report["ready"] is False
    assert report["object_relation"]["participant_to_vehicle_affine_receiver_ready"] is False
    assert report["blockers"][0]["id"] == "actual-participant-to-embedded-vehicle-affine-receiver-unproven"
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_wrong_retail_identity_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unexpected retail executable identity"):
        MODULE.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
            _retail_root(tmp_path, bad_md5=True),
            _instruction_export(tmp_path, _rows()),
        )


def test_instruction_set_drift_is_rejected(tmp_path: Path) -> None:
    rows = _rows()
    rows.pop(MODULE.VEHICLE_BASE_CTOR)
    path = tmp_path / "bad.jsonl"
    payload: list[dict] = []
    for address, instructions in rows.items():
        spec = MODULE.FUNCTIONS[address]
        payload.append(
            {
                "format": MODULE.INSTRUCTION_FORMAT,
                "program": MODULE.PROGRAM,
                "requested": spec["name"],
                "found": True,
                "function": {
                    "address": address,
                    "name": spec["name"],
                    "size": spec["size"],
                    "calling_convention": spec["calling_convention"],
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        )
    _write_jsonl(path, payload)
    with pytest.raises(ValueError, match="targeted instruction set drift"):
        MODULE.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
            _retail_root(tmp_path), path
        )
