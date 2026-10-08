from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_007b0710_collision_provider_frontier.json"
PHASE370 = ROOT / "evidence/collision_query_runtime_phase370.json"
RUNTIME = ROOT / "src/physics/collision_query_runtime.py"
WORLD = ROOT / "evidence/fun_00765c40_selected_bmw_world_position_join.json"
CACHE = ROOT / "evidence/fun_00765c40_query_cache_lifetime.json"
FALLBACK = ROOT / "evidence/fun_00765c40_selected_bmw_query_fallback.json"
HANDOFF = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"
DOC = ROOT / "docs/PROCESS_1_FUN_007B0710_COLLISION_PROVIDER_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontier_reuses_the_existing_pc_query_boundary() -> None:
    frontier = _load(FRONTIER)
    phase370 = _load(PHASE370)

    assert frontier["format"] == "SHIFT.Fun007b0710CollisionProviderFrontier/1"
    assert frontier["ready"] is True
    assert frontier["authority"]["semantic_platform"] == "PC retail primary"
    assert frontier["authority"]["new_machine_or_source_claims_in_this_join"] is False

    surface = frontier["known_call_surface"]
    assert surface["caller"] == phase370["source"]["wheel_caller_line"] and False
