from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_body0_construction_pose_stores.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_construction_pose_stores", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _varnode(
    text: str,
    *,
    space: str = "register",
    offset: str = "0x0",
    size: int = 4,
    constant: bool = False,
    register: bool | None = None,
    unique: bool | None = None,
) -> dict:
    if register is None:
        register = space == "register"
    if unique is None:
        unique = space == "unique"
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _pcode(opcode: str, text: str, *, output=None, inputs=None) -> dict:
    return {
        "opcode": opcode,
        "text": text,
        "output": output,
        "inputs": [] if inputs is None else inputs,
    }


def _instruction(
    address: int,
    mnemonic: str,
    operands: list[str],
    pcode: list[dict],
    *,
    fallthrough: int | None,
) -> dict:
    return {
        "address": f"0x{address:08x}",
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "flow_type": "TERMINATOR" if mnemonic == "RET" else "FALL_THROUGH",
        "fallthrough": None if fallthrough is None else f"0x{fallthrough:08x}",
        "flows": [],
        "references": [],
        "pcode": pcode,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _instruction_row(m, address: str, instructions: list[dict]) -> dict:
    return {
        "format": m.INSTRUCTION_FORMAT,
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "entry": address,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(
    tmp_path: Path,
    *,
    target: str | None = None,
    operand: str = "[ECX + 0xd4]",
    value_register: str = "EAX",
    fingerprint_drift: bool = False,
    omit_target: str | None = None,
) -> tuple[Path, Path]:
    m = _module()
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": m.PROGRAM, "executable_md5": m.PE_MD5}),
        encoding="utf-8",
    )

    function_rows = []
    for address in m.TARGETS:
        digest = m.FINGERPRINTS[address]
        if fingerprint_drift and address == m.BODY_BUILDER:
            digest = "0" * 64
        function_rows.append(
            {
                "address": address,
                "name": f"FUN_{address[2:]}",
                "thunk": False,
                "external": False,
                "mnemonic_sha256": digest,
            }
        )
    _write_jsonl(root / "functions.jsonl", function_rows)

    ram = _varnode(
        "ram", space="const", offset="0x1", constant=True, register=False, unique=False
    )
    registers = {
        "EAX": _varnode("EAX", offset="0x10"),
        "ECX": _varnode("ECX", offset="0x20"),
        "EBP": _varnode("EBP", offset="0x30"),
    }

    rows = []
    for address in m.TARGETS:
        if address == omit_target:
            continue
        start = int(address, 0)
        if address == target:
            base_text = operand.split("[", 1)[1].split("+", 1)[0].strip().rstrip("]")
            base_register = "EBP" if base_text.upper().startswith("EBP") else "ECX"
            value = registers[value_register]
            instructions = [
                _instruction(
                    start,
                    "MOV",
                    [operand, value_register],
                    [
                        _pcode(
                            "STORE",
                            f"STORE ram, {base_register}, {value_register}",
                            inputs=[ram, registers[base_register], value],
                        )
                    ],
                    fallthrough=start + 1,
                ),
                _instruction(start + 1, "RET", [], [], fallthrough=None),
            ]
        else:
            instructions = [_instruction(start, "RET", [], [], fallthrough=None)]
        rows.append(_instruction_row(m, address, instructions))

    export = tmp_path / "instructions.jsonl"
    _write_jsonl(export, rows)
    return root, export


def test_finds_exact_pose_store_without_promoting_semantics(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(tmp_path, target="0x007bbb10")
    report = m.analyze_bmw_body0_construction_pose_stores(root, export)

    assert report["format"] == m.FORMAT
    assert report["handoff"]["construction_pose_store_discovery_complete"] is True
    assert report["handoff"]["construction_pose_store_candidate_found"] is True
    assert report["handoff"]["BODY0_pointer_at_construction_pose_write_ready"] is False
    assert report["handoff"]["BODY0_bind_origin_basis_values_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False

    candidates = report["analysis"]["object_base_pose_store_candidates"]
    assert len(candidates) == 1
    row = candidates[0]
    assert row["function"] == "0x007bbb10"
    assert row["displacement"] == 0xD4
    assert row["store_width"] == 4
    assert row["pose_fields_touched"] == ["basis+0xd4"]
    assert row["base_register_origins"] == ["entry:ECX"]
    assert row["pcode_store_proven"] is True
    assert row["terminal_root_kinds"] == ["general-register"]
    assert row["persistent_BODY_target_identity_proven"] is False
    assert row["bind_value_semantics_proven"] is False


def test_frame_relative_pose_offset_is_not_object_candidate(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(
        tmp_path,
        target="0x007bbb60",
        operand="[EBP + 0xd4]",
    )
    report = m.analyze_bmw_body0_construction_pose_stores(root, export)

    assert report["analysis"]["object_base_pose_store_candidates"] == []
    assert len(report["analysis"]["frame_base_pose_store_candidates"]) == 1
    assert report["handoff"]["construction_pose_store_candidate_found"] is False
    assert any(
        row["id"] == "construction-pose-writer-not-found-in-target-set"
        for row in report["blockers"]
    )


def test_complex_store_target_blocks_completeness(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(
        tmp_path,
        target=m.BODY_BUILDER,
        operand="[ECX + EDX*4 + 0xd4]",
    )
    report = m.analyze_bmw_body0_construction_pose_stores(root, export)

    assert report["handoff"]["construction_pose_store_discovery_complete"] is False
    assert report["analysis"]["structural_blockers"]
    assert any(
        row["id"] == "construction-pose-store-structural-ambiguity"
        for row in report["blockers"]
    )


def test_missing_targeted_function_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(tmp_path, omit_target="0x007bbb60")
    with pytest.raises(ValueError, match="targeted construction instruction set mismatch"):
        m.analyze_bmw_body0_construction_pose_stores(root, export)


def test_retail_function_fingerprint_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(tmp_path, fingerprint_drift=True)
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        m.analyze_bmw_body0_construction_pose_stores(root, export)


def test_non_pose_store_is_not_candidate(tmp_path: Path) -> None:
    m = _module()
    root, export = _fixture(
        tmp_path,
        target="0x007bba90",
        operand="[ECX + 0x120]",
    )
    report = m.analyze_bmw_body0_construction_pose_stores(root, export)
    assert report["analysis"]["pose_overlap_store_candidates"] == []
    assert report["handoff"]["construction_pose_store_candidate_found"] is False
