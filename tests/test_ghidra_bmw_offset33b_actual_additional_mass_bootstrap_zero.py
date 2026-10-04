from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_actual_additional_mass_bootstrap_zero.py"
SPEC = importlib.util.spec_from_file_location("bmw_actual_additional_mass_zero", TOOL)
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


def test_positive_proof_uses_actual_object_and_allocator_zero_fill(tmp_path):
    report = MODULE.analyze(_root(tmp_path))

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "actual-additional-mass-bootstrap-zero-ready"
    assert report["object_graph"]["actual_participant_allocation_size"] == 0x2B90
    assert report["object_graph"]["embedded_vehicle_offset"] == 0x340
    assert report["object_graph"]["participant_additional_mass_offset"] == 0xBA0
    assert report["object_graph"]["vehicle_additional_mass_offset"] == 0x860
    assert report["object_graph"]["manager_record_plus_0xba0_is_not_the_proven_storage"] is True
    assert report["allocation_proof"]["requested_flags"] == 0x20
    assert report["allocation_proof"]["zero_fill_callsite"] == "0x00657be7"
    assert report["allocation_proof"]["zero_fill_operation"] == "memset(allocation, 0, requested_size)"
    assert report["proven_value"]["bits"] == "0x00000000"
    assert report["handoff"]["offset33b_actual_additional_mass_bootstrap_zero_ready"] is True
    assert report["handoff"]["offset33b_additional_mass_term_can_be_elided_for_first_bootstrap"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["retracted_manager_record_zero_claim_reused"] is False
    assert report["scope"]["reinitialized_or_reused_actual_participant_lifetime_proven"] is False


def test_alias_arithmetic_targets_actual_participant_storage():
    assert MODULE.PARTICIPANT_ADDITIONAL_MASS_OFFSET - MODULE.VEHICLE_OFFSET == MODULE.VEHICLE_ADDITIONAL_MASS_OFFSET
    assert MODULE.PARTICIPANT_ADDITIONAL_MASS_OFFSET + MODULE.TARGET_WIDTH <= MODULE.ACTUAL_PARTICIPANT_SIZE


def test_rejects_allocator_fingerprint_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "functions.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["address"] == "0x00657ab0":
            row["mnemonic_sha256"] = "0" * 64
    _write_jsonl(root / "functions.jsonl", rows)
    with pytest.raises(ValueError, match="0x00657ab0 mnemonic fingerprint drift"):
        MODULE.analyze(root)


def test_rejects_missing_zero_fill_callsite(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["instruction"] != "0x00657be7"]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="0x00657ab0:0x00657be7"):
        MODULE.analyze(root)


def test_rejects_constructor_chain_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["instruction"] != "0x0072ed57"]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="0x0072ed20:0x0072ed57"):
        MODULE.analyze(root)


def test_rejects_pre_initvehicle_ordering_drift(tmp_path):
    root = _root(tmp_path)
    rows = [json.loads(line) for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["instruction"] != "0x0074dddb"]
    _write_jsonl(root / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="0x0074ddc3:0x0074dddb"):
        MODULE.analyze(root)


def test_rejects_wrong_retail_identity(tmp_path):
    root = _root(tmp_path)
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": "0" * 32}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unexpected retail executable identity"):
        MODULE.analyze(root)
