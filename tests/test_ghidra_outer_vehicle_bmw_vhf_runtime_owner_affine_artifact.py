from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_bmw_vhf_runtime_owner_affine_join.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_bmw_vhf_runtime_owner_affine_artifact", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_committed_runtime_owner_affine_join_is_exact_regeneration():
    bridge = _load(ROOT / "evidence" / "process1_outer_vehicle_render_snapshot_affine_bridge.json")
    bmw_join = _load(ROOT / "evidence" / "process1_bmw_vehicle_render_model_resource_join.json")
    committed = _load(
        ROOT / "evidence" / "process1_outer_vehicle_bmw_vhf_runtime_owner_affine_join.json"
    )

    assert MODULE.analyze(bridge, bmw_join) == committed
    assert committed["ready"] is True
    assert committed["handoff"]["outer_vehicle_affine_to_canonical_BMW_VHF_runtime_owner_ready"] is True
    assert committed["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert committed["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert committed["handoff"]["BODY0_bind_frame_proof_ready"] is False
