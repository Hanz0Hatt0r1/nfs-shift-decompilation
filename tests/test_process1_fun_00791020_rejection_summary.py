import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "evidence/process1_fun_00791020_rejection_summary.json"


def test_summary_keeps_p1_3_open_and_provider_count_unchanged() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Fun00791020RejectionSummary/1"
    assert payload["primary_contract"] == "SHIFT.Fun00791020HDVehicleRejection/1"
    assert payload["next_absolute_writer_offsets"] == ["0x938", "0x13b8", "0x1e38", "0x28b8"]
    assert payload["p1_3_control_producer_complete"] is False
    assert payload["external_provider_count"] == 7
