from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    tools = str(root / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    spec = importlib.util.spec_from_file_location(
        "validate_native_vertical_slice_runtime_inputs_tested",
        root / "tools" / "validate_native_vertical_slice_runtime_inputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_keyboard_choice_is_validated_as_input_binding_without_artifact(tmp_path):
    mod = _load_module()
    rows = mod.validate_explicit_runtime_inputs(
        workspace_root=tmp_path,
        explicit_inputs={},
        keyboard=True,
    )

    assert rows["input_binding"]["ready"] is True
    assert rows["input_binding"]["artifact"] is None
    assert rows["input_binding"]["validation"]["mode"] == "keyboard"
    assert rows["input_binding"]["boundary"]["launcher_validator_reused"] is True


def test_input_script_reuses_exact_launcher_parser(tmp_path):
    mod = _load_module()
    script = tmp_path / "input.txt"
    script.write_text(
        "SHIFT.NativeRuntimeInputScript/1\n"
        "0 1 0 0 0\n"
        "1 0 1 0 0\n",
        encoding="utf-8",
    )
    rows = mod.validate_explicit_runtime_inputs(
        workspace_root=tmp_path,
        explicit_inputs={},
        input_script=script,
    )

    assert rows["input_binding"]["ready"] is True
    assert rows["input_binding"]["validation"]["steps"] == 2
    assert rows["input_binding"]["validation"]["mode"] == "script"


def test_participant_boundary_requires_same_identity_admission_as_launcher(tmp_path):
    mod = _load_module()
    participant = tmp_path / "participant.json"
    participant.write_text(
        json.dumps({
            "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "ready": True,
            "registry_selector_identity_join_proven": False,
            "participant_instance_ready": True,
        }),
        encoding="utf-8",
    )
    rows = mod.validate_explicit_runtime_inputs(
        workspace_root=tmp_path,
        explicit_inputs={"participant_boundary": participant},
        keyboard=True,
    )

    row = rows["participant_boundary"]
    assert row["ready"] is False
    assert any(
        "no proven registry/selector identity join" in reason
        for reason in row["blocking_reasons"]
    )
    assert row["boundary"]["path_presence_is_proof"] is False


def test_path_outside_workspace_is_rejected_before_contract_validation(tmp_path):
    mod = _load_module()
    outside = tmp_path.parent / "outside-camera.json"
    outside.write_text(
        json.dumps({"format": "SHIFT.NativeCameraStateBridge/1", "ready": True}),
        encoding="utf-8",
    )
    rows = mod.validate_explicit_runtime_inputs(
        workspace_root=tmp_path,
        explicit_inputs={"camera_state": outside},
        keyboard=True,
    )

    row = rows["camera_state"]
    assert row["ready"] is False
    assert any("path-escapes-workspace" in reason for reason in row["blocking_reasons"])
