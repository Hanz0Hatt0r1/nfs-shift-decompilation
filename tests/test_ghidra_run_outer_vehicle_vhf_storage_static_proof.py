from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_outer_vehicle_vhf_storage_static_proof.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_vhf_storage_runner", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _receiver_report(path: Path, direct: tuple[str, ...]) -> dict:
    rows = []
    for spec in MODULE._storage._receivers.SINK_CALLS:
        callee = spec["callee"]
        is_direct = callee in direct
        rows.append(
            {
                **spec,
                "ECX_origins_before_call": (
                    ["entry:ECX"] if is_direct else ["memory:[esi+0x20]"]
                ),
                "ECX_origin_deterministic": True,
                "ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths": is_direct,
                "same_ECX_origin_expression_set_as_HDVehicle_sink": (
                    callee != MODULE._storage.HDVEHICLE_SETTER and not is_direct
                ),
            }
        )
    report = {
        "format": MODULE._storage.RECEIVER_FORMAT,
        "ready": True,
        "status": "receiver-frontier-ready",
        "sink_receiver_analyses": rows,
        "handoff": {
            "outer_setter_sink_ECX_provenance_evaluated": True,
            "outer_setter_sink_ECX_provenance_unambiguous": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return report


def _install_receiver_runner(monkeypatch, output_dir: Path, direct: tuple[str, ...]):
    def fake_receiver_runner(*args, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        _receiver_report(output_dir / MODULE._receiver_runner.RECEIVER_FILE, direct)
        bundle = {
            "format": MODULE._receiver_runner.FORMAT,
            "completed": True,
            "handoff": {"outer_setter_sink_ECX_provenance_ready": True},
        }
        (output_dir / MODULE._receiver_runner.BUNDLE_FILE).write_text(
            json.dumps(bundle), encoding="utf-8"
        )
        return bundle

    monkeypatch.setattr(
        MODULE._receiver_runner,
        "run_outer_vehicle_vhf_receiver_static_proof",
        fake_receiver_runner,
    )


def _run_args(tmp_path: Path) -> tuple:
    return (
        tmp_path / "ghidra-project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "symbolic.json",
        tmp_path / "out",
    )


def test_unique_receiver_target_exports_exact_function_and_runs_storage(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "out"
    _install_receiver_runner(monkeypatch, output_dir, ("0x007876e0",))
    observed: dict[str, object] = {}

    def fake_subprocess(command, env, check):
        observed["command"] = list(command)
        observed["env"] = dict(env)
        assert check is True
        Path(command[5]).write_text("fixture\n", encoding="utf-8")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_subprocess)

    def fake_storage(ghidra_export, receiver_path, instruction_path):
        assert receiver_path == output_dir / MODULE._receiver_runner.RECEIVER_FILE
        assert instruction_path == output_dir / MODULE.STORAGE_INSTRUCTION_FILE
        return {
            "format": MODULE._storage.FORMAT,
            "ready": True,
            "status": "storage-domain-ready",
            "exact_outer_receiver_field_spans": [
                {
                    "function": "0x007876e0",
                    "offset": 16,
                    "offset_hex": "0x10",
                    "size": 16,
                }
            ],
            "handoff": {"outer_vehicle_transform_storage_domain_ready": True},
        }

    monkeypatch.setattr(
        MODULE._storage,
        "analyze_outer_vehicle_transform_storage_domain",
        fake_storage,
    )

    report = MODULE.run_outer_vehicle_vhf_storage_static_proof(
        *_run_args(tmp_path), ghidra_home=tmp_path / "ghidra-home"
    )

    assert report["format"] == MODULE.FORMAT
    assert report["status"] == "storage-domain-ready"
    assert report["selected_storage_targets"] == ["0x007876e0"]
    assert report["selected_storage_function_tokens"] == ["FUN_007876e0"]
    assert observed["command"][-1:] == ["FUN_007876e0"]
    assert report["handoff"]["outer_vehicle_transform_storage_domain_ready"] is True
    assert report["handoff"]["outer_vehicle_transform_field_spans_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["hardcoded_storage_sink_selected"] is False
    assert (output_dir / MODULE.BUNDLE_FILE).is_file()


def test_multiple_selected_targets_are_exported_together_in_address_order(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "out"
    direct = ("0x007afb60", "0x007876e0")
    _install_receiver_runner(monkeypatch, output_dir, direct)
    commands: list[list[str]] = []

    def fake_subprocess(command, env, check):
        commands.append(list(command))
        Path(command[5]).write_text("fixture\n", encoding="utf-8")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_subprocess)
    monkeypatch.setattr(
        MODULE._storage,
        "analyze_outer_vehicle_transform_storage_domain",
        lambda *args: {
            "format": MODULE._storage.FORMAT,
            "ready": True,
            "status": "storage-domain-frontier",
            "exact_outer_receiver_field_spans": [],
            "handoff": {"outer_vehicle_transform_storage_domain_ready": False},
        },
    )

    report = MODULE.run_outer_vehicle_vhf_storage_static_proof(
        *_run_args(tmp_path), ghidra_home=tmp_path / "ghidra-home"
    )

    assert report["selected_storage_targets"] == ["0x007876e0", "0x007afb60"]
    assert commands[0][-2:] == ["FUN_007876e0", "FUN_007afb60"]
    assert report["status"] == "storage-domain-frontier"
    assert report["decision"]["class"] == "resolve-storage-domain-frontier"
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False


def test_zero_selected_targets_skip_second_ghidra_export_and_storage_analyzer(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "out"
    _install_receiver_runner(monkeypatch, output_dir, ())

    def forbidden(*args, **kwargs):
        raise AssertionError("downstream storage work must not execute with zero targets")

    monkeypatch.setattr(MODULE.subprocess, "run", forbidden)
    monkeypatch.setattr(
        MODULE._storage,
        "analyze_outer_vehicle_transform_storage_domain",
        forbidden,
    )

    report = MODULE.run_outer_vehicle_vhf_storage_static_proof(
        *_run_args(tmp_path), ghidra_home=tmp_path / "ghidra-home"
    )

    assert report["completed"] is True
    assert report["status"] == "blocked-by-receiver-routing"
    assert report["selected_storage_targets"] == []
    assert report["stages"]["storage_instruction_export"]["state"] == "blocked_by_upstream_gate"
    assert report["scope"]["zero_target_Ghidra_export_attempted"] is False
    assert report["handoff"]["outer_vehicle_transform_storage_domain_ready"] is False


def test_second_export_failure_preserves_failure_bundle(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    _install_receiver_runner(monkeypatch, output_dir, ("0x007876e0",))

    def failed_export(*args, **kwargs):
        raise RuntimeError("targeted export failed")

    monkeypatch.setattr(MODULE.subprocess, "run", failed_export)

    with pytest.raises(RuntimeError, match="targeted export failed"):
        MODULE.run_outer_vehicle_vhf_storage_static_proof(
            *_run_args(tmp_path), ghidra_home=tmp_path / "ghidra-home"
        )

    bundle = json.loads((output_dir / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "storage_instruction_export"
    assert bundle["selected_storage_targets"] == ["0x007876e0"]
    assert bundle["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert bundle["scope"]["partial_artifacts_preserved"] is True


def test_storage_failure_preserves_selected_target_and_failure_bundle(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "out"
    _install_receiver_runner(monkeypatch, output_dir, ("0x007876e0",))

    def fake_subprocess(command, env, check):
        Path(command[5]).write_text("fixture\n", encoding="utf-8")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_subprocess)
    monkeypatch.setattr(
        MODULE._storage,
        "analyze_outer_vehicle_transform_storage_domain",
        lambda *args: (_ for _ in ()).throw(ValueError("storage proof failed")),
    )

    with pytest.raises(ValueError, match="storage proof failed"):
        MODULE.run_outer_vehicle_vhf_storage_static_proof(
            *_run_args(tmp_path), ghidra_home=tmp_path / "ghidra-home"
        )

    bundle = json.loads((output_dir / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "storage_domain"
    assert bundle["selected_storage_targets"] == ["0x007876e0"]
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False


def test_retail_program_name_and_timeout_fail_closed_before_work(tmp_path):
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_outer_vehicle_vhf_storage_static_proof(
            *_run_args(tmp_path),
            program_name="OTHER.exe",
            ghidra_home=tmp_path / "ghidra-home",
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_outer_vehicle_vhf_storage_static_proof(
            *_run_args(tmp_path),
            timeout_seconds=0,
            ghidra_home=tmp_path / "ghidra-home",
        )
