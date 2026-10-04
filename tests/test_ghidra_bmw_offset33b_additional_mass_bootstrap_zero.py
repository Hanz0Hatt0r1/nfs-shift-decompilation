from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_additional_mass_bootstrap_zero.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_additional_mass_bootstrap_zero", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _retail_root(
    tmp_path: Path,
    *,
    fingerprint_override: tuple[str, str] | None = None,
    drop_call: tuple[str, str, str] | None = None,
    source_anchor_function_override: tuple[str, str] | None = None,
) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )

    functions: list[dict] = []
    for address, expected in MODULE.FUNCTIONS.items():
        sha = expected["mnemonic_sha256"]
        if fingerprint_override is not None and address == fingerprint_override[0]:
            sha = fingerprint_override[1]
        functions.append(
            {
                "address": address,
                "name": expected["name"],
                "namespace": "Global",
                "size": expected["size"],
                "thunk": False,
                "external": False,
                "calling_convention": expected["calling_convention"],
                "signature": "synthetic",
                "parameters": [],
                "mnemonic_sha256": sha,
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    calls: list[dict] = []
    for source, instruction, target, _role in MODULE.REQUIRED_CALLS:
        if drop_call == (source, instruction, target):
            continue
        calls.append(
            {
                "from_function": source,
                "from_name": MODULE.FUNCTIONS.get(source, {}).get("name", "synthetic"),
                "instruction": instruction,
                "to": target,
                "to_name": MODULE.FUNCTIONS.get(target, {}).get("name", "synthetic"),
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", calls)

    anchors: list[dict] = []
    for index, (value, expected_function) in enumerate(MODULE.SOURCE_ANCHORS):
        function = expected_function
        if source_anchor_function_override is not None and value == source_anchor_function_override[0]:
            function = source_anchor_function_override[1]
        anchors.append(
            {
                "address": f"0x00b{index:05x}",
                "value": value,
                "length": len(value) + 1,
                "xrefs": [f"0x00a{index:05x}"],
                "functions": [function],
            }
        )
    _write_jsonl(root / "strings_xrefs.jsonl", anchors)
    return root


def test_positive_contract_closes_only_additional_mass_zero_root(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(_retail_root(tmp_path))

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "additional-mass-bootstrap-zero-ready"

    proof = report["proof"]
    assert proof["participant_record_stride"] == 0x1FA0
    assert proof["constructor"]["zero_helper_argument"] == "participant + 0xb00"
    assert proof["reinitialized_slot_reset"]["zero_helper_argument"] == "participant + 0xb00"
    assert proof["recovered_zero_helper_semantics"]["target_subobject_offset"] == 0xA0
    assert proof["recovered_zero_helper_semantics"]["target_is_inside_zero_range"] is True
    assert proof["storage_alias"]["participant_additional_mass_offset"] == 0xBA0
    assert proof["storage_alias"]["vehicle_additional_mass_offset"] == 0x860
    assert proof["bootstrap_preservation"]["value_preserved_until_Vehicle_InitVehicle"] is True
    assert proof["offset33b_root"]["consumer_producer"] == "0x0076b280"
    assert proof["offset33b_root"]["value_bits"] == "0x00000000"
    assert proof["offset33b_root"]["value"] == 0.0
    assert proof["offset33b_root"]["numeric_value_proven"] is True

    gates = report["gates"]
    assert gates["offset33b_additional_mass_bootstrap_zero_ready"] is True
    assert gates["offset33b_additional_mass_term_can_be_elided_for_first_bootstrap"] is True
    assert gates["BMW_numeric_offset33b_ready"] is False
    assert gates["BODY0_to_outer_vehicle_root_numeric_matrix_ready"] is False
    assert gates["BODY0_bind_frame_proof_ready"] is False
    assert gates["vehicle_world_transform_ready"] is False
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["remaining_HDV_VDF_SDF_tire_roots_evaluated"] is False


def test_rejects_zero_helper_fingerprint_drift(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="0x00552dd0 mnemonic_sha256 drift"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(
                tmp_path,
                fingerprint_override=("0x00552dd0", "0" * 64),
            )
        )


def test_rejects_missing_constructor_zero_helper_call(tmp_path: Path) -> None:
    edge = ("0x00714360", "0x007143c9", "0x00552dd0")
    with pytest.raises(ValueError, match="required direct call drift"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(tmp_path, drop_call=edge)
        )


def test_rejects_missing_reused_slot_reset_call(tmp_path: Path) -> None:
    edge = ("0x007126a0", "0x007126db", "0x00552dd0")
    with pytest.raises(ValueError, match="required direct call drift"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(tmp_path, drop_call=edge)
        )


def test_rejects_restart_to_InitVehicle_ordering_edge_drift(tmp_path: Path) -> None:
    edge = ("0x0074ddc3", "0x0074de12", "0x00798df0")
    with pytest.raises(ValueError, match="required direct call drift"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(tmp_path, drop_call=edge)
        )


def test_rejects_source_anchor_drift(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no longer belongs"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(
                tmp_path,
                source_anchor_function_override=(
                    "MWL::Core::Vehicle::InitVehicle",
                    "0x0074ddc3",
                ),
            )
        )


def test_rejects_wrong_retail_binary(tmp_path: Path) -> None:
    root = _retail_root(tmp_path)
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": "0" * 32}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unexpected retail executable identity"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(root)
