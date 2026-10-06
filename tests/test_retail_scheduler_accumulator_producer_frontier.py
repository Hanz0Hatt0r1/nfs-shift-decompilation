import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence" / "retail_scheduler_accumulator_producer_frontier.json"


def _load():
    return json.loads(FRONTIER.read_text(encoding="utf-8"))


def test_frontier_stays_fail_closed_for_retail_cadence():
    payload = _load()
    assert payload["format"] == "SHIFT.SchedulerAccumulatorRetailExecutionFrontier/1"
    assert payload["status"] == "frontier"
    assert payload["retail_cadence_admitted"] is False
    assert payload["gates_changed"] == []


def test_only_actual_positive_inputs_are_classified_positive():
    payload = _load()
    assert payload["upstream_positive"] == [
        "SHIFT.PhysicsManagerSchedulerEntryOwner/1",
        "SHIFT.OuterUpdateCallsiteStatic/1",
    ]
    infra = {
        row["format"]: row for row in payload["merged_proof_infrastructure_not_yet_a_retail_result"]
    }
    assert infra["SHIFT.SchedulerAccumulatorProducerFrontier/1"]["retail_machine_result_published"] is False
    assert infra["SHIFT.SchedulerAccumulatorValueProvenance/1"]["retail_machine_result_published"] is False


def test_frontier_keeps_exact_scheduler_anchors():
    anchors = _load()["anchors"]
    assert anchors["upper_caller"] == "0x007155e9"
    assert anchors["scheduler_owner"] == "0x00715380"
    assert anchors["batch_scheduler"] == "0x00713050"
    assert anchors["upper_to_owner_callsite"] == "0x00715602"
    assert anchors["owner_to_batch_callsite"] == "0x00715434"
    assert anchors["scheduler_accumulator_offset"] == "0x348"
    assert anchors["scheduler_rate_offset"] == "0x388"


def test_frontier_requires_actual_retail_slice_before_value_promotion():
    payload = _load()
    assert payload["current_shortest_edge"]["id"] == "retail-targeted-scheduler-slice-execution"
    blockers = {row["id"] for row in payload["remaining_blockers"]}
    assert {
        "retail-targeted-scheduler-slice-execution",
        "accumulator-writer-surface",
        "accumulator-param1-value-dependency",
        "upper-caller-pushed-value-producer",
        "controller-runtime-dispatch",
        "retail-rate-source",
    } == blockers
    rejected = "\n".join(payload["rejected_promotions"])
    assert "analyzer format" in rejected
    assert "rendered frame" in rejected
    assert "closed BODY integration" in rejected
