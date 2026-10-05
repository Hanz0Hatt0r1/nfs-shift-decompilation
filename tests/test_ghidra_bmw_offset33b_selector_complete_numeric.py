from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_selector_complete_numeric.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_selector_complete_numeric", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _retail_root(tmp_path: Path) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir(parents=True)
    _write_json(root / "binary.json", {
        "program_name": MODULE.PROGRAM,
        "executable_md5": MODULE.PE_MD5,
    })
    functions = []
    for address, (name, size, convention, digest) in MODULE.TARGETS.items():
        functions.append({
            "address": address,
            "name": name,
            "size": size,
            "calling_convention": convention,
            "mnemonic_sha256": digest,
            "external": False,
            "thunk": False,
        })
    _write_jsonl(root / "functions.jsonl", functions)
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "indirect": False,
            }
            for source, instruction, target in sorted(MODULE.REQUIRED_DIRECT_EDGES)
        ],
    )
    strings = []
    for value, (address, function, xref) in MODULE.EXPECTED_STRINGS.items():
        strings.append({
            "address": address,
            "value": value,
            "functions": [function],
            "xrefs": [xref],
        })
    _write_jsonl(root / "strings_xrefs.jsonl", strings)
    return root


def _resource_inputs(tmp_path: Path) -> Path:
    bodies = [
        {"index": 0, "name": "body", "mass": 0.0},
        {"index": 1, "name": "fl_spindle", "mass": 18.0},
        {"index": 2, "name": "fr_spindle", "mass": 18.0},
        {"index": 3, "name": "fl_wheel", "mass": 25.0},
        {"index": 4, "name": "fr_wheel", "mass": 25.0},
        {"index": 5, "name": "rl_spindle", "mass": 17.0},
        {"index": 6, "name": "rr_spindle", "mass": 17.0},
        {"index": 7, "name": "rl_wheel", "mass": 26.0},
        {"index": 8, "name": "rr_wheel", "mass": 26.0},
        {"index": 9, "name": "fuel_tank", "mass": 1.0},
        {"index": 10, "name": "driver_head", "mass": 5.0},
    ]
    return _write_json(tmp_path / "resources.json", {
        "format": MODULE.RESOURCE_FORMAT,
        "ready": True,
        "cdf": {
            "decoded_sha256": MODULE.EXPECTED_GEOMETRY["cdf_sha"],
            "values": {
                "Mass": 1460.0,
                "CGHeight": 0.28,
                "GraphicalOffset": [0.0, 0.0, 0.0],
                "FuelTankPos": [0.0, 0.2, -0.6],
                "FuelTankMotion": [560.0, 0.7],
            },
        },
        "sdf": {"bodies": bodies},
    })


def _additional_mass(tmp_path: Path) -> Path:
    return _write_json(tmp_path / "additional.json", {
        "format": MODULE.ADDITIONAL_MASS_FORMAT,
        "ready": True,
        "handoff": {
            "offset33b_actual_additional_mass_bootstrap_zero_ready": True,
        },
        "proven_value": {"bits": "0x00000000", "value": 0.0},
    })


def _reference_y(tmp_path: Path) -> Path:
    return _write_json(tmp_path / "reference_y.json", {
        "format": MODULE.REFERENCE_Y_FORMAT,
        "ready": True,
        "handoff": {
            "offset33b_vehicle_reference_y_bootstrap_zero_ready": True,
        },
        "offset33b_join": {
            "reduced_expression": "-effective_graphical_offset_y",
        },
    })


def _geometry(tmp_path: Path) -> Path:
    source = json.loads(
        (ROOT / "evidence" / "bmw_offset33b_selector_geometry_inputs.json").read_text(
            encoding="utf-8"
        )
    )
    return _write_json(tmp_path / "geometry.json", source)


def _analyze(tmp_path: Path):
    return MODULE.analyze(
        _retail_root(tmp_path),
        _resource_inputs(tmp_path),
        _additional_mass(tmp_path),
        _reference_y(tmp_path),
        _geometry(tmp_path),
    )


def test_selector_complete_family_proves_three_unique_translations(tmp_path):
    report = _analyze(tmp_path)

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "selector-complete-numeric-family-ready"

    geometry = report["bootstrap_geometry"]
    assert geometry["corrected_wheel_points"]["fl"] == pytest.approx(
        [0.711, 0.0125, -1.35]
    )
    assert geometry["corrected_wheel_points"]["rl"] == pytest.approx(
        [0.7225, 0.0025, 1.35]
    )
    assert geometry["auxiliary_mass"] == pytest.approx(173.0)
    assert geometry["BODY0_mass"] == pytest.approx(1287.0)
    assert geometry["mass_ratio"] == pytest.approx(173.0 / 1287.0)
    assert geometry["auxiliary_weighted_COM"] == pytest.approx(
        [0.0, 0.008525908340214699, 0.004335260115606936]
    )
    assert geometry["target_CG_x"] == pytest.approx(0.0)
    assert geometry["target_CG_z"] == pytest.approx(-0.081)

    family = report["selector_family"]
    assert len(family) == 6
    assert len(report["unique_BODY0_to_outer_vehicle_root_translations"]) == 3

    normal_1 = next(
        row for row in family
        if row["use_drift_cgheight_scale"] is False
        and row["player_difficulty"] == 1
    )
    normal_2 = next(
        row for row in family
        if row["use_drift_cgheight_scale"] is False
        and row["player_difficulty"] == 2
    )
    drift_2 = next(
        row for row in family
        if row["use_drift_cgheight_scale"] is True
        and row["player_difficulty"] == 2
    )
    assert normal_1["BODY0_to_outer_vehicle_root_translation"] == pytest.approx(
        [0.0, 0.02143668831168831, -0.011470862470862471]
    )
    assert normal_2["BODY0_to_outer_vehicle_root_translation"] == pytest.approx(
        [0.0, 0.02708237595737596, -0.011470862470862471]
    )
    assert drift_2["BODY0_to_outer_vehicle_root_translation"] == pytest.approx(
        [0.0, 0.008263417138417138, -0.011470862470862471]
    )

    handoff = report["handoff"]
    assert handoff["offset33b_auxiliary_weighted_COM_ready"] is True
    assert handoff["offset33b_target_CG_selector_family_ready"] is True
    assert handoff["BMW_numeric_offset33b_selector_family_ready"] is True
    assert handoff["BODY0_to_outer_vehicle_root_selector_family_ready"] is True
    assert handoff["BMW_numeric_offset33b_ready_when_race_mode_selector_bound"] is True
    assert handoff["BMW_numeric_offset33b_ready"] is False
    assert handoff["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert handoff["BODY0_bind_frame_proof_ready"] is False
    assert handoff["vehicle_world_transform_ready"] is False


def test_rejects_player_difficulty_index_three(tmp_path):
    geometry = json.loads(_geometry(tmp_path).read_text(encoding="utf-8"))
    geometry["selector_contract"]["valid_player_difficulty"] = [0, 1, 2, 3]
    path = _write_json(tmp_path / "geometry_bad.json", geometry)
    with pytest.raises(ValueError, match="Player Difficulty domain drift"):
        MODULE.analyze(
            _retail_root(tmp_path / "other"),
            _resource_inputs(tmp_path / "other"),
            _additional_mass(tmp_path / "other"),
            _reference_y(tmp_path / "other"),
            path,
        )


def test_rejects_vdf_geometry_drift(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    geometry = json.loads(_geometry(root).read_text(encoding="utf-8"))
    geometry["vdf"]["wheel_dimensions"]["fl"][0] = 0.3
    path = _write_json(root / "geometry_bad.json", geometry)
    with pytest.raises(ValueError, match="wheel_dimensions.fl drift"):
        MODULE.analyze(
            _retail_root(root),
            _resource_inputs(root),
            _additional_mass(root),
            _reference_y(root),
            path,
        )


def test_rejects_reference_y_proof_drift(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    reference = json.loads(_reference_y(root).read_text(encoding="utf-8"))
    reference["offset33b_join"]["reduced_expression"] = "unknown"
    path = _write_json(root / "reference_bad.json", reference)
    with pytest.raises(ValueError, match="reduced expression drift"):
        MODULE.analyze(
            _retail_root(root),
            _resource_inputs(root),
            _additional_mass(root),
            path,
            _geometry(root),
        )


def test_rejects_retail_function_fingerprint_drift(tmp_path):
    root = _retail_root(tmp_path)
    rows = [
        json.loads(line)
        for line in (root / "functions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rows[0]["mnemonic_sha256"] = "0" * 64
    _write_jsonl(root / "functions.jsonl", rows)
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        MODULE.analyze(
            root,
            _resource_inputs(tmp_path),
            _additional_mass(tmp_path),
            _reference_y(tmp_path),
            _geometry(tmp_path),
        )


def test_committed_selector_complete_contract_keeps_final_frame_gate_closed():
    report = json.loads(
        (ROOT / "evidence" / "bmw_offset33b_selector_complete_numeric.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert len(report["selector_family"]) == 6
    assert len(report["unique_BODY0_to_outer_vehicle_root_translations"]) == 3
    assert report["handoff"]["BMW_numeric_offset33b_selector_family_ready"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
