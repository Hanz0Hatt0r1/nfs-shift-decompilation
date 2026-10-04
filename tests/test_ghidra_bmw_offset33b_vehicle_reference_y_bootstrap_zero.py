from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_vehicle_reference_y_bootstrap_zero.py"
SPEC = importlib.util.spec_from_file_location("bmw_reference_y_zero", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    functions = []
    for address, expected in MODULE.FUNCTIONS.items():
        name, size, cc, fingerprint, _role = expected
        functions.append(
            {
                "address": address,
                "name": name,
                "namespace": "Global",
                "size": size,
                "thunk": False,
                "external": False,
                "calling_convention": cc,
                "signature": "synthetic",
                "parameters": [],
                "mnemonic_sha256": fingerprint,
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)
    calls = [
        {
            "from_function": source,
            "from_name": MODULE.FUNCTIONS.get(source, ("external",))[0],
            "instruction": instruction,
            "to": target,
            "to_name": MODULE.FUNCTIONS.get(target, ("external",))[0],
            "indirect": False,
        }
        for source, instruction, target, _role in MODULE.REQUIRED_CALLS
    ]
    _write_jsonl(root / "callgraph.jsonl", calls)
    return root


def test_positive_reference_y_constructor_zero(tmp_path):
    report = MODULE.analyze(_root(tmp_path))

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["object_graph"]["actual_participant_read_offset"] == 0x500
    assert report["object_graph"]["vehicle_field_offset"] == 0x1C0
    assert report["constructor_proof"]["stored_bits"] == "0x00000000"
    assert report["offset33b_join"]["producer_receiver_resolution"] == "**(HDVehicle+0x3fe8) == actual_participant"
    assert report["offset33b_join"]["reduced_expression"] == "-effective_graphical_offset_y"
    assert report["offset33b_join"]["effective_graphical_offset_y_numeric_value_proven"] is False
    assert report["handoff"]["offset33b_vehicle_reference_y_bootstrap_zero_ready"] is True
    assert report["handoff"]["offset33b_reference_y_reduced_to_negative_graphical_offset"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["additional_mass_zero_proven_by_this_contract"] is False


def test_alias_and_constructor_index_are_exact():
    assert MODULE.ACTUAL_PARTICIPANT_REFERENCE_Y_OFFSET - MODULE.VEHICLE_OFFSET == MODULE.VEHICLE_REFERENCE_Y_OFFSET
    assert MODULE.VEHICLE_REFERENCE_Y_DWORD_INDEX * 4 == MODULE.VEHICLE_REFERENCE_Y_OFFSET


def test_rejects_base_vehicle_constructor_fingerprint_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "functions.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["address"] == "0x0079bfd0":
            row["mnemonic_sha256"] = "0" * 64
    _write_jsonl(root / "functions.jsonl", rows)
    with pytest.raises(ValueError, match="0x0079bfd0 mnemonic_sha256 drift"):
        MODULE.analyze(root)


def test_rejects_constructor_chain_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["instruction"] != "0x0079c1e1"]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="0x0079c1c0:0x0079c1e1"):
        MODULE.analyze(root)


def test_rejects_hdvehicle_join_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["instruction"] != "0x0076e270"]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="0x0076df50:0x0076e270"):
        MODULE.analyze(root)


def test_rejects_wrong_retail_program(tmp_path):
    root = _root(tmp_path)
    (root / "binary.json").write_text(
        json.dumps({"program_name": "OTHER.exe", "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unexpected retail program name"):
        MODULE.analyze(root)
