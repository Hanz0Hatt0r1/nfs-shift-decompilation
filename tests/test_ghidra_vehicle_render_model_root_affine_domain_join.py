from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "tools" / "ghidra" / "analyze_vehicle_render_model_root_affine_domain_join.py"
spec = importlib.util.spec_from_file_location("domain_join", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = "\n".join(
        [
            "puVar13 = *(undefined1 **)(*(int *)((int)param_1 + 0xf0) + 0x54);",
            "FUN_006362e0(local_64,puVar13);",
            "FUN_004aecd0((int *)((int)param_1 + 0x1340),&local_158);",
            "FUN_0042fc90(local_50,(undefined4 *)(param_1 + 0x1028));",
            "local_20 = *(undefined4 *)(param_1 + 0xa10);",
            "local_1c = *(undefined4 *)(param_1 + 0xa14);",
            "local_18 = *(undefined4 *)(param_1 + 0xa18);",
            "FUN_004a8c20(param_1 + 0x1340,local_50);",
            "pfVar2 = (float *)(param_1 + 0x918);",
            "local_30 = param_2[8] * *pfVar2 + pfVar2[-2] * *param_2 + param_2[4] * pfVar2[-1] + param_2[0xc];",
            "local_2c = param_2[9] * *pfVar2 + param_2[1] * pfVar2[-2] + param_2[5] * pfVar2[-1] + param_2[0xd];",
            "local_28 = param_2[10] * *pfVar2 + param_2[2] * pfVar2[-2] + param_2[6] * pfVar2[-1] + param_2[0xe];",
            "FUN_00693940(pfVar1,*(int *)(local_14 + 0x174),uVar3,pfVar4);",
        ]
    )
    source_path = tmp_path / "SHIFT.exe.c"
    source_path.write_text(source, encoding="utf-8")
    monkeypatch.setattr(module, "SOURCE_SHA256", hashlib.sha256(source.encode()).hexdigest())

    ghidra = tmp_path / "db"
    ghidra.mkdir()
    with (ghidra / "functions.jsonl").open("w", encoding="utf-8") as handle:
        for address, (name, size, convention, fingerprint) in module.TARGETS.items():
            handle.write(
                json.dumps(
                    {
                        "address": address,
                        "name": name,
                        "size": size,
                        "calling_convention": convention,
                        "mnemonic_sha256": fingerprint,
                    }
                )
                + "\n"
            )

    resource = {
        "format": module.RESOURCE_JOIN_FORMAT,
        "ready": True,
        "retail": {"program": module.PROGRAM, "md5": module.PE_MD5},
        "input_owner_proof": {
            "vehicle_render_hierarchy_owner_ready": True,
            "vehicle_render_model_property_name": "Vehicle Render Model",
            "vehicle_render_model_property_field": "+0x54",
        },
        "selected_vehicle_descriptor": {
            "vehicle_name": "BMW_M3_E36",
            "property_value": "BMW_M3_E36.vhf",
            "selected_BMW_vehicle_render_model_value_ready": True,
        },
        "canonical_bmw_vhf_resource": {
            "resolved_path": module.CANONICAL_VHF,
            "decoded_sha256": module.DECODED_VHF_SHA256,
            "canonical_BMW_VHF_resource_join_ready": True,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
    }
    resource_path = tmp_path / "resource.json"
    resource_path.write_text(json.dumps(resource), encoding="utf-8")

    affine = {
        "format": module.AFFINE_BRIDGE_FORMAT,
        "ready": True,
        "retail": {
            "program": module.PROGRAM,
            "md5": module.PE_MD5,
            "source_sha256": module.SOURCE_SHA256,
        },
        "outer_transform": {
            "local_delta_has_concrete_setup_producer": True,
            "local_delta_is_runtime_pose_source": False,
            "render_root_local_delta_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "independent_rotation_source_present": False,
        },
        "render_participant_relation": {
            "vehicle_render_model": "participant+0x1340",
            "derived_rotation_matrix": "participant+0x1028",
            "root_translation": ["participant+0xa10", "participant+0xa14", "participant+0xa18"],
            "world_affine_consumed_by": "FUN_004a8c20",
            "world_affine_translation_slots": [12, 13, 14],
            "node_local_FUN_004ae150_promoted_to_root_setter": False,
        },
        "handoff": {
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
        },
    }
    affine_path = tmp_path / "affine.json"
    affine_path.write_text(json.dumps(affine), encoding="utf-8")
    return ghidra, source_path, resource_path, affine_path


def test_positive_domain_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _write_inputs(tmp_path, monkeypatch)
    report = module.analyze_vehicle_render_model_root_affine_domain_join(*inputs)
    assert report["format"] == module.FORMAT
    assert report["ready"] is True
    assert report["proof"]["vehicle_render_model_root_affine_domain_join_ready"] is True
    assert report["participant_domain"]["vehicle_render_model_owner"] == "participant+0x1340"
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["limits"]["hierarchy_root_matrix_applied_or_composed_here"] is False


def test_rejects_resource_preclaim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = list(_write_inputs(tmp_path, monkeypatch))
    path = inputs[2]
    value = json.loads(path.read_text())
    value["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="preclaims outer/VHF"):
        module.analyze_vehicle_render_model_root_affine_domain_join(*inputs)


def test_rejects_affine_consumer_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = list(_write_inputs(tmp_path, monkeypatch))
    path = inputs[3]
    value = json.loads(path.read_text())
    value["render_participant_relation"]["world_affine_consumed_by"] = "FUN_deadbeef"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="world-affine consumer drift"):
        module.analyze_vehicle_render_model_root_affine_domain_join(*inputs)


def test_rejects_function_fingerprint_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = list(_write_inputs(tmp_path, monkeypatch))
    functions = inputs[0] / "functions.jsonl"
    rows = [json.loads(line) for line in functions.read_text().splitlines()]
    rows[1]["mnemonic_sha256"] = "0" * 64
    functions.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        module.analyze_vehicle_render_model_root_affine_domain_join(*inputs)


def test_rejects_missing_local_point_transform_witness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = list(_write_inputs(tmp_path, monkeypatch))
    source = inputs[1]
    text = source.read_text().replace("param_2[0xe]", "param_2[0xb]")
    source.write_text(text)
    monkeypatch.setattr(module, "SOURCE_SHA256", hashlib.sha256(text.encode()).hexdigest())
    with pytest.raises(ValueError, match="missing FUN_004a8c20 source witness"):
        module.analyze_vehicle_render_model_root_affine_domain_join(*inputs)
