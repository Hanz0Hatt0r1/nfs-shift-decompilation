from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_bootstrap_mass_ratio.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_bootstrap_mass_ratio", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _ghidra_root(tmp_path: Path, *, omit_lookup: str | None = None) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    functions = []
    for address, (name, size, convention, digest) in MODULE.TARGETS.items():
        functions.append(
            {
                "address": address,
                "name": name,
                "size": size,
                "calling_convention": convention,
                "mnemonic_sha256": digest,
                "external": False,
                "thunk": False,
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    callgraph = [
        {
            "from_function": source,
            "instruction": instruction,
            "to": target,
            "indirect": False,
        }
        for source, instruction, target in MODULE.REQUIRED_DIRECT_EDGES
    ]
    for instruction in MODULE.LOOKUP_CALLS:
        if instruction == omit_lookup:
            continue
        callgraph.append(
            {
                "from_function": "0x007615c0",
                "instruction": instruction,
                "to": "0x007b3da0",
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", callgraph)
    return root


def _resource_path(tmp_path: Path, *, include_rear_axle: bool = False) -> Path:
    bodies = [
        (0, "body", 0.0),
        (1, "fl_spindle", 18.0),
        (2, "fr_spindle", 18.0),
        (3, "fl_wheel", 25.0),
        (4, "fr_wheel", 25.0),
        (5, "rl_spindle", 17.0),
        (6, "rr_spindle", 17.0),
        (7, "rl_wheel", 26.0),
        (8, "rr_wheel", 26.0),
        (9, "fuel_tank", 1.0),
        (10, "driver_head", 5.0),
    ]
    if include_rear_axle:
        bodies.append((11, "rear_axle", 3.0))
    value = {
        "format": MODULE.RESOURCE_FORMAT,
        "ready": True,
        "cdf": {"values": {"Mass": 1460.0}},
        "sdf": {
            "bodies": [
                {"index": index, "name": name, "mass": mass}
                for index, name, mass in bodies
            ]
        },
        "handoff": {
            "offset33b_resource_inputs_ready": True,
            "offset33b_direct_CDF_load_data_mapping_ready": True,
            "offset33b_SDF_body_resource_values_ready": True,
            "BMW_numeric_offset33b_ready": False,
        },
        "scope": {"runtime_BODY_mass_equals_raw_SDF_mass_assumed": False},
    }
    path = tmp_path / "resources.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _additional_path(tmp_path: Path, *, value: float = 0.0) -> Path:
    report = {
        "format": MODULE.ADDITIONAL_MASS_FORMAT,
        "ready": True,
        "handoff": {
            "offset33b_actual_additional_mass_bootstrap_zero_ready": True,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
        },
        "proven_value": {"type": "float32", "value": value},
        "object_graph": {
            "participant_additional_mass_offset": 0xBA0,
            "vehicle_additional_mass_offset": 0x860,
        },
    }
    path = tmp_path / "additional.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_exact_bmw_first_bootstrap_mass_ratio(tmp_path: Path) -> None:
    report = MODULE.analyze(
        _ghidra_root(tmp_path),
        _resource_path(tmp_path),
        _additional_path(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "bootstrap-mass-ratio-proven"
    terms = report["mass_terms"]
    assert terms["corner_body_mass_sum"] == 172.0
    assert terms["auxiliary_mass"] == 173.0
    assert terms["BODY0_mass"] == 1287.0
    assert terms["auxiliary_to_BODY0_mass_ratio"] == pytest.approx(173.0 / 1287.0)
    assert terms["driver_head_mass"] == 5.0
    assert terms["driver_head_excluded_from_body0_mass_subtraction"] is True
    assert terms["rear_axle_present"] is False
    assert report["handoff"]["offset33b_mass_ratio_ready"] is True
    assert report["handoff"]["offset33b_auxiliary_weighted_COM_ready"] is False
    assert report["handoff"]["offset33b_target_CG_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["scope"]["bootstrap_runtime_mass_join_is_construction_order_specific"] is True


def test_corner_pairs_are_each_43kg_in_exact_bmw_resource(tmp_path: Path) -> None:
    report = MODULE.analyze(
        _ghidra_root(tmp_path),
        _resource_path(tmp_path),
        _additional_path(tmp_path),
    )
    masses = {row["name"]: row["mass"] for row in report["mass_terms"]["corner_bodies"]}
    assert masses["fl_wheel"] + masses["fl_spindle"] == 43.0
    assert masses["fr_wheel"] + masses["fr_spindle"] == 43.0
    assert masses["rl_wheel"] + masses["rl_spindle"] == 43.0
    assert masses["rr_wheel"] + masses["rr_spindle"] == 43.0


def test_missing_body_lookup_edge_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="BODY lookup callsite set drift"):
        MODULE.analyze(
            _ghidra_root(tmp_path, omit_lookup="0x007617bb"),
            _resource_path(tmp_path),
            _additional_path(tmp_path),
        )


def test_unexpected_rear_axle_body_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unexpectedly contains rear_axle"):
        MODULE.analyze(
            _ghidra_root(tmp_path),
            _resource_path(tmp_path, include_rear_axle=True),
            _additional_path(tmp_path),
        )


def test_nonzero_additional_mass_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not exact float32 zero"):
        MODULE.analyze(
            _ghidra_root(tmp_path),
            _resource_path(tmp_path),
            _additional_path(tmp_path, value=1.0),
        )
