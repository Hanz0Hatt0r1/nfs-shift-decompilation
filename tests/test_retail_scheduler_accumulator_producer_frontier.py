import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence" / "retail_scheduler_accumulator_producer_frontier.json"


def _load():
    return json.loads(FRONTIER.read_text(encoding="utf-8"))


def test_frontier_stays_fail_closed_for_retail_cadence():
    payload = _load()
    assert payload["format"] == "SHIFT.SchedulerAccumulatorCallerValueProducerFrontier/1"
    assert payload["status"] == "frontier"
    assert payload["retail_cadence_admitted"] is False
    assert payload["gates_changed"] == []


def test_frontier_consumes_merged_accumulator_value_proof():
    payload = _load()
    assert "SHIFT.SchedulerAccumulatorValueProvenance/1" in payload["upstream_positive"]
    proven = "\n".join(row["fact"] for row in payload["proven_facts"])
    assert "this+0x348" in proven
    assert "param_1" in proven


def test_frontier_keeps_exact_upper_callsite_and_scheduler_anchors():
    anchors = _load()["anchors"]
    assert anchors["upper_caller"] == "0x007155e9"
    assert anchors["scheduler_owner"] == "0x00715380"
    assert anchors["upper_to_owner_callsite"] == "0x00715602"
    assert anchors["scheduler_accumulator_offset"] == "0x348"
    assert anchors["scheduler_rate_offset"] == "0x388"


def test_frontier_preserves_only_remaining_s5_boundaries():
    payload = _load()
    blockers = {row["id"] for row in payload["remaining_blockers"]}
    assert blockers == {
        "upper-caller-pushed-value-producer",
        "physical-time-unit-semantics",
        "controller-runtime-dispatch",
        "retail-rate-source",
    }
    assert "accumulator-write-provenance" not in blockers
    rejected = "\n".join(payload["rejected_promotions"])
    assert "rendered frame" in rejected
    assert "host wall-clock dt" in rejected
    assert "closed BODY integration" in rejected
