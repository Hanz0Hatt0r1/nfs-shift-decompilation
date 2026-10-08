import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_blocker_graph_ids_are_unique():
    payload = json.loads((ROOT / "coordination/decomp_blockers.json").read_text(encoding="utf-8"))
    ids = []
    for stream in payload["workstreams"]:
        ids.append(stream["id"])
        ids.extend(child["id"] for child in stream.get("children", []))
    assert len(ids) == len(set(ids))


def test_blocker_graph_provider_reduction_is_not_preapplied():
    payload = json.loads((ROOT / "coordination/decomp_blockers.json").read_text(encoding="utf-8"))
    assert payload["rules"]["external_provider_count"] == 7
    p23 = next(row for row in payload["workstreams"] if row["id"] == "P2.3")
    assert p23["status"] == "blocked"
    assert p23["provider_reduction_on_completion"] == "7 -> 6"
