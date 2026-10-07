from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_surface_probe_node_cache.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007675f0_surface_probe_node_cache.hpp"
PHASE732 = ROOT / "evidence/fun_007675f0_surface_probe_join.json"


def test_pc_cache_owner_and_refresh_policy_are_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0SurfaceProbeNodeCache/1"
    assert payload["ready"] is True
    assert payload["source"]["program"] == "SHIFT.exe"
    assert payload["source"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["caller"] == "FUN_00769ef0"
    assert payload["source"]["consumer"] == "FUN_007675f0"
    assert payload["source"]["probe"] == "FUN_00759210"
    assert payload["source"]["lookup"] == "FUN_00717cd0"

    state = payload["retail_state"]
    assert state["node_owner"] == "HDVehicle"
    assert state["node_offset"] == "0x120"
    assert state["last_body_position_offsets"] == ["0x128", "0x130", "0x138"]
    assert state["initial_node_value"] is None

    refresh = payload["refresh_policy"]
    assert refresh["threshold_constant"] == 0.01
    assert refresh["comparison"] == (
        "refresh iff cached node is null OR squared displacement > 0.01"
    )
    assert refresh["strict"] is True
    assert refresh["null_lookup_result_still_commits_last_position"] is True
    assert refresh["null_lookup_result_forces_next_lookup"] is True


def test_machine_evidence_hashes_are_pinned() -> None:
    spans = json.loads(EVIDENCE.read_text(encoding="utf-8"))["machine_spans"]
    assert spans["initial_null_store"]["sha256"] == (
        "de80b36bed29776616c009c0abe76601e1307616daf37eb9cff54c9a39723e76"
    )
    assert spans["cache_read_and_threshold"]["sha256"] == (
        "d1b6ae07d28e252c3052439021aca99b156fda78c14608f9ceddcc93b281b222"
    )
    assert spans["lookup_refresh_and_commit"]["sha256"] == (
        "27baa0aff6297df0c93c8c3f560b68488225f9e67d3bf96d2b8d604ed2ab7913"
    )
    assert spans["FUN_007675f0_call"]["sha256"] == (
        "8158017874872b7e9e0081b19dbaef498aae92521bbeb67fd635e149c200f090"
    )
    assert spans["consumer_argument_to_probe"]["sha256"] == (
        "cbed8328d98af36c84aa468075045b78445144e2c1f0577c461c7847ed1c1479"
    )
    assert spans["threshold_constant"]["bytes_le"] == "7c14ae47e17a843f"
    assert spans["threshold_constant"]["sha256"] == (
        "e563d3f39c6f51ac0a5a149f4fc6ff180c02a95e443f4d4ea0625ab589fa8260"
    )


def test_native_helper_keeps_lookup_external_and_strict() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun007675f0SurfaceProbeNodeCache/1" in header
    assert "kFun007675f0SurfaceProbeNodeOffset = 0x120u" in header
    assert "kFun007675f0SurfaceProbeLastPositionXOffset = 0x128u" in header
    assert "kFun007675f0SurfaceProbeLastPositionYOffset = 0x130u" in header
    assert "kFun007675f0SurfaceProbeLastPositionZOffset = 0x138u" in header
    assert "kFun007675f0SurfaceProbeRefreshDistanceSquared = 0.01" in header
    assert "Fun00717cd0SurfaceProbeNodeLookupProvider" in header
    assert ">\n        kFun007675f0SurfaceProbeRefreshDistanceSquared" in header
    assert "cache.node == nullptr" in header
    assert "lookup_provider(query_position, previous_node)" in header
    assert "cache.last_body_position = current_body_position" in header


def test_phase733_does_not_overclaim_runtime_wiring() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    scope = payload["scope"]
    assert handoff["cache_policy_native"] is True
    assert handoff["lookup_behavior_native"] is False
    assert handoff["wired_into_NativeVehicleProviderSession"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["surface_probe_node_direct_per_pass_boundary_removed"] is False
    assert scope["world_node_graph_internalized"] is False

    phase732 = json.loads(PHASE732.read_text(encoding="utf-8"))
    assert phase732["format"] == "SHIFT.Fun007675f0SurfaceProbeJoin/1"
    assert phase732["ready"] is True
