import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "evidence/process1_p1_3_absolute_writer_frontier.json"


def test_absolute_writer_frontier_evidence_is_fail_closed() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1P13AbsoluteWriterFrontier/1"
    assert payload["rejected_candidate_contract"] == "SHIFT.Fun00791020HDVehicleRejection/1"
    assert payload["raw_numeric_offset_match_is_ownership_proof"] is False
    assert payload["retail_input_control_provenance_proven"] is False
    assert payload["p1_3_control_producer_complete"] is False
    assert payload["external_provider_count"] == 7
